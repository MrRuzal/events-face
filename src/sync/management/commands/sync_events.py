import time
from datetime import datetime, timedelta
import uuid

import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.conf import settings

from events.models import Event, Venue
from src.common import logger
from sync.models import SyncResult

BASE_URL = settings.EVENTS_FACE.get(
    "BASE_URL", "https://events.k3scluster.tech/api/events/"
)
MAX_RETRIES = settings.EVENTS_FACE.get("MAX_RETRIES", 3)
DEFAULT_BATCH_SIZE = settings.EVENTS_FACE.get("DEFAULT_BATCH_SIZE", 500)
DEFAULT_TIMEOUT = settings.EVENTS_FACE.get("DEFAULT_TIMEOUT", 10)


def perform_request_with_retries(
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES,
    backoff: int = 2,
):
    """
    Выполняет GET-запрос с повторными попытками при сетевых ошибках и ошибках HTTP.

    :param url: URL для запроса.
    :param timeout: Время ожидания ответа.
    :param max_retries: Максимальное количество попыток.
    :param backoff: Время ожидания между попытками.
    :return: Response объект при успешном запросе, None при неудаче.
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=timeout, verify=True)
            if response.status_code == 404:
                logger.warning(f"Resource not found (404) at {url}")
                return None
            elif response.status_code >= 500:
                logger.error(
                    f"Server error {response.status_code} on attempt {attempt} for URL {url}"
                )
                if attempt < max_retries:
                    logger.warning(f"Retrying in {backoff} seconds...")
                    time.sleep(backoff)
                else:
                    return None
            elif 400 <= response.status_code < 500:
                logger.error(
                    f"Client error {response.status_code} for URL {url}"
                )
                return None
            else:
                response.raise_for_status()
                logger.info(
                    f"Successful response from {url} on attempt {attempt}"
                )
                return response
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                logger.warning(
                    f"Attempt {attempt} failed: {e}. Retrying in {backoff} seconds..."
                )
                time.sleep(backoff)
            else:
                logger.error(
                    f"Failed to fetch events after {max_retries} attempts: {e}"
                )
                return None


class Command(BaseCommand):
    """
    Класс команд управления Django для синхронизации событий с внешним поставщиком событий.
    """

    help = "Synchronize events with the events-provider"

    def add_arguments(self, parser):
        """
        Добавляет аргументы командной строки для управления поведением синхронизации.

        :param parser: Экземпляр ArgumentParser, к которому добавляются аргументы.
        """
        parser.add_argument(
            "--date",
            type=str,
            help="Date for synchronization in YYYY-MM-DD format",
        )
        parser.add_argument(
            "--all", action="store_true", help="Synchronize all events"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=DEFAULT_BATCH_SIZE,
            help="Batch size for bulk operations (default: 500)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run synchronization without saving data to the database",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of events to process",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=DEFAULT_TIMEOUT,
            help="Timeout for HTTP requests in seconds",
        )
        parser.add_argument(
            "--max-retries",
            type=int,
            default=MAX_RETRIES,
            help="Maximum number of retries for HTTP requests",
        )

    def fetch_with_retries(
        self,
        url: str,
        max_retries: int = MAX_RETRIES,
        backoff: int = 2,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Достает данные из URL с логикой повторных попыток при сетевых ошибках и ошибках HTTP.

        param: URL для извлечения данных.
        param: Максимальное количество попыток.
        param: Время ожидания перед повторной попыткой.

        return: Объект Response в случае успеха, None в противном случае.
        """
        return perform_request_with_retries(
            url=url, timeout=timeout, max_retries=max_retries, backoff=backoff
        )

    def log_metrics(self, new_events_count: int, updated_events_count: int):
        """
        Логирует метрики синхронизации.

        param: Количество новых созданных событий.
        param: Количество обновленных событий.
        """
        self.stdout.write(
            self.style.SUCCESS(
                f"Synchronization complete. New: {new_events_count}, Updated: {updated_events_count}"
            )
        )

    def bulk_process(self, items, model, update_fields=None):
        """
        Выполняет пакетную обработку объектов с использованием bulk_create или bulk_update.

        :param items: Список объектов модели для обработки.
        :param model: Модель Django.
        :param update_fields: Список полей для обновления при bulk_update. Если None, используется bulk_create.
        """
        batch_size = self.batch_size
        with transaction.atomic():
            for i in range(0, len(items), batch_size):
                batch = items[i : i + batch_size]
                if update_fields is None:
                    model.objects.bulk_create(batch, batch_size=batch_size)
                else:
                    model.objects.bulk_update(
                        batch, update_fields, batch_size=batch_size
                    )

    def _sync_events(self, events_data):
        """
        Синхронизирует события и площадки на основе полученных данных.

        param: Список данных событий
        """
        if not isinstance(events_data, list):
            self.stderr.write(
                self.style.ERROR(
                    "Invalid response format: expected a list of events"
                )
            )
            return

        if self.limit is not None:
            events_data = events_data[: self.limit]

        venue_ids = set()
        event_ids = set()
        skipped_count = 0

        valid_events = []
        for ev in events_data:
            if not isinstance(ev, dict):
                logger.warning("Skipping event due to invalid data structure")
                skipped_count += 1
                continue

            ev_id = ev.get("id")
            try:
                uuid_obj = uuid.UUID(str(ev_id))
            except (ValueError, TypeError):
                logger.warning(
                    f"Skipping event due to invalid UUID id: {ev_id}"
                )
                skipped_count += 1
                continue

            name = ev.get("name")
            if not isinstance(name, str) or not name.strip():
                logger.warning(
                    f"Skipping event due to empty or invalid name: {ev_id}"
                )
                skipped_count += 1
                continue
            if len(name) > 255:
                logger.warning(
                    f"Skipping event due to name too long (>255 chars): {ev_id}"
                )
                skipped_count += 1
                continue

            event_time_raw = ev.get("event_time")
            event_time = parse_datetime(event_time_raw)
            if event_time is None:
                logger.warning(
                    f"Skipping event due to invalid event_time format: {ev_id}"
                )
                skipped_count += 1
                continue

            status = ev.get("status", "open")
            if status not in ("open", "closed"):
                logger.warning(
                    f"Invalid status '{status}' for event {ev_id}, setting to 'open'"
                )
                status = "open"
            ev["status"] = status

            valid_events.append(ev)
            event_ids.add(ev_id)
            venue_data = ev.get("venue")
            if (
                venue_data
                and isinstance(venue_data, dict)
                and venue_data.get("id") is not None
            ):
                venue_ids.add(venue_data["id"])

        self.stdout.write(
            self.style.NOTICE(f"Total events received: {len(events_data)}")
        )
        self.stdout.write(
            self.style.NOTICE(
                f"Events skipped due to validation: {skipped_count}"
            )
        )

        existing_venues = Venue.objects.filter(id__in=venue_ids)
        venue_map = {v.id: v for v in existing_venues}

        existing_events = Event.objects.select_related('venue').filter(
            id__in=event_ids
        )
        event_map = {e.id: e for e in existing_events}

        new_venues = []
        for ev in valid_events:
            venue_data = ev.get("venue")
            if (
                venue_data
                and isinstance(venue_data, dict)
                and venue_data.get("id") is not None
            ):
                vid = venue_data["id"]
                if vid not in venue_map:
                    new_venues.append(
                        Venue(id=vid, name=venue_data.get("name", ""))
                    )
        if new_venues:
            if not self.dry_run:
                self.bulk_process(new_venues, Venue)

            for v in new_venues:
                venue_map[v.id] = v

        new_events = []
        events_to_update = []
        fields_to_check = ["name", "event_time", "status", "venue_id"]

        for ev in valid_events:
            ev_id = ev["id"]
            venue_data = ev.get("venue")
            venue = None
            if (
                venue_data
                and isinstance(venue_data, dict)
                and venue_data.get("id") is not None
            ):
                venue = venue_map.get(venue_data["id"])

            event_time = parse_datetime(ev.get("event_time"))

            status = ev.get("status", "open")
            name = ev.get("name")

            existing_event = event_map.get(ev_id)
            if existing_event:
                changed = False
                for field in fields_to_check:
                    new_value = None
                    if field == "venue_id":
                        new_value = venue.id if venue else None
                    else:
                        new_value = locals()[field]
                    if getattr(existing_event, field) != new_value:
                        setattr(
                            existing_event,
                            field if field != "venue_id" else "venue_id",
                            new_value,
                        )
                        changed = True
                if changed:
                    events_to_update.append(existing_event)
            else:
                new_events.append(
                    Event(
                        id=ev_id,
                        name=name,
                        event_time=event_time,
                        status=status,
                        venue=venue,
                    )
                )

        if not self.dry_run:
            if new_events:
                self.bulk_process(new_events, Event)
            if events_to_update:
                self.bulk_process(
                    events_to_update,
                    Event,
                    update_fields=["name", "event_time", "status", "venue"],
                )

            SyncResult.objects.create(
                new_events_count=len(new_events),
                updated_events_count=len(events_to_update),
            )

        self.log_metrics(len(new_events), len(events_to_update))

    def handle(self, *args, **kwargs):
        """
        Точка входа для выполнения команды, определяет параметры и запускает синхронизацию.

        param: Позиционные аргументы.
        param: Ключевые аргументы команды.
        """
        self.batch_size = kwargs.get("batch_size", DEFAULT_BATCH_SIZE)
        date_str = kwargs.get("date")
        all_flag = kwargs.get("all", False)
        self.dry_run = kwargs.get("dry_run", False)
        self.limit = kwargs.get("limit")
        self.timeout = kwargs.get("timeout", DEFAULT_TIMEOUT)
        self.max_retries = kwargs.get("max_retries", MAX_RETRIES)

        if all_flag:
            all_events = []
            url = BASE_URL
            page_number = 1
            while url:
                response = self.fetch_with_retries(
                    url, max_retries=self.max_retries, timeout=self.timeout
                )
                if response is None:
                    break
                try:
                    data = response.json()
                except ValueError:
                    self.stderr.write(
                        self.style.ERROR("Failed to parse JSON response")
                    )
                    break
                events_page = (
                    data.get("results") if isinstance(data, dict) else None
                )
                if events_page is None:
                    if isinstance(data, list):
                        events_page = data
                        url = None
                    else:
                        self.stderr.write(
                            self.style.ERROR("Unexpected JSON format")
                        )
                        break
                all_events.extend(events_page)
                logger.info(
                    f"Fetched page {page_number} with {len(events_page)} events"
                )
                next_url = data.get("next") if isinstance(data, dict) else None
                url = next_url
                page_number += 1
            self._sync_events(all_events)
        else:
            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    self.stderr.write(self.style.ERROR("Invalid date format"))
                    return
            else:
                date_obj = datetime.now().date() - timedelta(days=1)

            url = f"{BASE_URL}?changed_at={date_obj}"

            response = self.fetch_with_retries(
                url, max_retries=self.max_retries, timeout=self.timeout
            )
            if response is None:
                return

            try:
                events_data = response.json()
            except ValueError:
                self.stderr.write(
                    self.style.ERROR("Failed to parse JSON response")
                )
                return

            self._sync_events(events_data)
