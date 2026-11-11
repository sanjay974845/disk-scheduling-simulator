"""Disk scheduling algorithms and movement calculations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence


ALGORITHMS = ("FCFS", "SSTF", "SCAN", "C-SCAN", "LOOK", "C-LOOK")
DIRECTIONAL_ALGORITHMS = ("SCAN", "C-SCAN", "LOOK", "C-LOOK")


@dataclass(frozen=True)
class Movement:
    start: int
    end: int
    distance: int
    kind: str
    serviced: bool


@dataclass(frozen=True)
class ScheduleResult:
    algorithm: str
    initial_head: int
    service_order: tuple[int, ...]
    path: tuple[int, ...]
    movements: tuple[Movement, ...]

    @property
    def total_movement(self) -> int:
        return sum(movement.distance for movement in self.movements)

    def as_dict(self) -> dict[str, object]:
        return {
            "algorithm": self.algorithm,
            "initial_head": self.initial_head,
            "service_order": list(self.service_order),
            "path": list(self.path),
            "movements": [asdict(movement) for movement in self.movements],
            "total_movement": self.total_movement,
        }


def parse_integer_list(text: str, label: str = "Values") -> list[int]:
    """Parse comma- or whitespace-separated integers with a useful error."""
    tokens = text.replace(",", " ").split()
    if not tokens:
        raise ValueError(f"{label} must contain at least one integer.")

    values: list[int] = []
    for token in tokens:
        try:
            values.append(int(token))
        except ValueError as exc:
            raise ValueError(f"{label} contains an invalid integer: {token!r}.") from exc
    return values


def calculate_sequence(sequence: Sequence[int]) -> list[dict[str, int]]:
    """Return one movement record for each adjacent pair in a sequence."""
    if not sequence:
        raise ValueError("Enter at least one cylinder position.")
    if any(not isinstance(position, int) or isinstance(position, bool) for position in sequence):
        raise ValueError("Cylinder positions must be integers.")

    return [
        {
            "step": index,
            "start": sequence[index - 1],
            "end": sequence[index],
            "distance": abs(sequence[index] - sequence[index - 1]),
        }
        for index in range(1, len(sequence))
    ]


def _validate_input(
    cylinders: int,
    head: int,
    requests: Sequence[int],
    algorithm: str,
    direction: str,
) -> tuple[str, str]:
    if not isinstance(cylinders, int) or isinstance(cylinders, bool) or cylinders < 1:
        raise ValueError("The number of cylinders must be a positive integer.")
    if not isinstance(head, int) or isinstance(head, bool) or not 0 <= head < cylinders:
        raise ValueError(f"The initial head must be between 0 and {cylinders - 1}.")
    if any(
        not isinstance(request, int)
        or isinstance(request, bool)
        or not 0 <= request < cylinders
        for request in requests
    ):
        raise ValueError(f"Every request must be between 0 and {cylinders - 1}.")

    selected_algorithm = algorithm.strip().upper()
    if selected_algorithm not in ALGORITHMS:
        raise ValueError(f"Choose one of: {', '.join(ALGORITHMS)}.")

    selected_direction = direction.strip().lower()
    if selected_direction not in ("left", "right"):
        raise ValueError("Direction must be 'left' or 'right'.")
    return selected_algorithm, selected_direction


def _build_result(
    algorithm: str,
    head: int,
    route: Sequence[tuple[int, str, bool]],
) -> ScheduleResult:
    path = [head]
    movements: list[Movement] = []
    service_order: list[int] = []
    current = head

    for destination, kind, serviced in route:
        movements.append(
            Movement(
                start=current,
                end=destination,
                distance=abs(destination - current),
                kind=kind,
                serviced=serviced,
            )
        )
        path.append(destination)
        current = destination
        if serviced:
            service_order.append(destination)

    return ScheduleResult(
        algorithm=algorithm,
        initial_head=head,
        service_order=tuple(service_order),
        path=tuple(path),
        movements=tuple(movements),
    )


def simulate(
    algorithm: str,
    cylinders: int,
    head: int,
    requests: Sequence[int],
    direction: str = "right",
) -> ScheduleResult:
    """Schedule requests and report the full head path, including scan travel."""
    selected_algorithm, selected_direction = _validate_input(
        cylinders, head, requests, algorithm, direction
    )
    queue = list(requests)
    route: list[tuple[int, str, bool]] = []

    if selected_algorithm == "FCFS":
        route.extend((request, "Request", True) for request in queue)
        return _build_result(selected_algorithm, head, route)

    if selected_algorithm == "SSTF":
        pending = list(enumerate(queue))
        current = head
        while pending:
            original_index, destination = min(
                pending,
                key=lambda item: (abs(item[1] - current), item[0]),
            )
            pending.remove((original_index, destination))
            route.append((destination, "Request", True))
            current = destination
        return _build_result(selected_algorithm, head, route)

    at_head = [request for request in queue if request == head]
    below = [request for request in queue if request < head]
    above = [request for request in queue if request > head]
    route.extend((request, "Request", True) for request in at_head)

    if selected_direction == "right":
        forward = sorted(above)
        reverse = sorted(below, reverse=True)
        circular = sorted(below)
        boundary = cylinders - 1
        circular_origin = 0
    else:
        forward = sorted(below, reverse=True)
        reverse = sorted(above)
        circular = sorted(above, reverse=True)
        boundary = 0
        circular_origin = cylinders - 1

    if selected_algorithm in ("SCAN", "C-SCAN"):
        route.extend((request, "Request", True) for request in forward)
        current = route[-1][0] if route else head

        if any(request != head for request in queue) and current != boundary:
            route.append((boundary, "Disk boundary", False))

        current = route[-1][0] if route else head
        if selected_algorithm == "SCAN":
            route.extend((request, "Request", True) for request in reverse)
        elif circular:
            if current != circular_origin:
                route.append((circular_origin, "Circular wrap", False))
            route.extend((request, "Request", True) for request in circular)
        return _build_result(selected_algorithm, head, route)

    route.extend((request, "Request", True) for request in forward)
    if selected_algorithm == "LOOK":
        route.extend((request, "Request", True) for request in reverse)
    elif circular:
        wrap_target = circular[0]
        route.append((wrap_target, "Circular wrap", False))
        route.extend((request, "Request", True) for request in circular)

    return _build_result(selected_algorithm, head, route)
