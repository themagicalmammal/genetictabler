"""Binary encoding and decoding for GA genes.

Each possible timetable entry — "course X is taught to class Y in slot Z" —
is encoded as a short binary string called a **gene**:

    gene = <course_bits> + <slot_bits> + <class_bits>
           "010"         + "00101"     + "011"
            course 2       slot 5        class 3
"""

from __future__ import annotations

import random

from genetictabler.config import TimetableConfig


class GeneEncoder:
    """Stateful encoder that knows bit-widths and range bounds."""

    def __init__(self, config: TimetableConfig) -> None:
        self.course_bits: int = 0
        self.slot_bits: int = 0
        self.class_bits: int = 0
        self.course_count: int = config.courses
        self.slot_count: int = config.slots
        self.day_count: int = config.days
        self.class_count: int = config.classes
        self.total_slots: int = config.slots * config.days

    def to_binary(self, value: int, bit_length: int) -> str:
        """Convert an integer to a zero-padded binary string of exactly ``bit_length``.

        Example:
            ``to_binary(5, 4)`` → ``'0101'``
        """
        raw = bin(value)[2:]
        return raw.zfill(bit_length)

    def encode_course(self) -> str:
        """Pick a random course (1 … course_count) and encode as binary."""
        return self.to_binary(random.randint(1, self.course_count), self.course_bits)

    def encode_slot(self) -> str:
        """Pick a random cumulative slot (1 … total_slots) and encode as binary."""
        return self.to_binary(random.randint(1, self.total_slots), self.slot_bits)

    def encode_class(self) -> str:
        """Pick a random class (1 … class_count) and encode as binary."""
        return self.to_binary(random.randint(1, self.class_count), self.class_bits)

    def generate_gene(self) -> str:
        """Build a complete random gene = course_bits + slot_bits + class_bits."""
        return self.encode_course() + self.encode_slot() + self.encode_class()

    def decode_gene(self, gene: str) -> tuple[int, int, int, int]:
        """Fully decode a gene string back into human-readable components.

        Returns:
            ``(course_no, slot_no, day_no, class_no)`` — all 1-based natural numbers.
        """
        course_no = int(gene[: self.course_bits], 2)
        slot_no, day_no = self.extract_slot_day(gene)
        class_no = int(gene[self.course_bits + self.slot_bits :], 2)
        return course_no, slot_no, day_no, class_no

    def extract_slot_day(self, gene: str) -> tuple[int, int]:
        """Convert the cumulative slot number into a ``(slot_within_day, day_number)`` pair.

        Uses 1-based slot_no and 0-based day_no internally.
        """
        raw_slot: int = int(
            gene[self.course_bits : self.course_bits + self.slot_bits], 2
        )
        slot_no = raw_slot % self.slot_count
        day_no = raw_slot // self.slot_count

        if slot_no == 0:  # perfect multiple → last slot of previous day
            slot_no = self.slot_count
            day_no -= 1

        return slot_no, day_no
