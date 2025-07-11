
from app.common.database.objects import DBChatFilter
from app.common.database import filters
from typing import List, Tuple

class ChatFilter:
    def __init__(self) -> None:
        self.filters: List[DBChatFilter] = []

    def __repr__(self) -> str:
        return f'<ChatFilter ({len(self.filters)} filters)>'

    def __len__(self) -> int:
        return len(self.filters)

    def populate(self) -> None:
        self.filters = filters.fetch_all()

    def apply(self, message: str) -> Tuple[str | None, int | None]:
        for chat_filter in self.filters:
            # Apply filter & check if content has changed
            replacement = chat_filter.replacement or ""
            filtered_message = chat_filter.regex_pattern.sub(replacement, message)
            is_filtered = filtered_message != message

            # Update message with filtered content
            message = filtered_message

            if not is_filtered:
                continue

            if not chat_filter.block:
                continue

            return None, chat_filter.timeout or 60

        return message, None
