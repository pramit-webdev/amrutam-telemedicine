from math import ceil


class PaginationParams:
    def __init__(self, page: int = 1, size: int = 20):
        self.page = max(1, page)
        self.size = min(100, max(1, size))

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


class PaginatedResponse:
    def __init__(self, items: list, total: int, params: PaginationParams):
        self.items = items
        self.total = total
        self.page = params.page
        self.size = params.size
        self.total_pages = ceil(total / params.size) if params.size > 0 else 0

    def dict(self) -> dict:
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "size": self.size,
            "total_pages": self.total_pages,
        }
