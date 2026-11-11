import unittest

from disk_scheduler import calculate_sequence, parse_integer_list, simulate


class DiskSchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cylinders = 200
        self.head = 53
        self.requests = [98, 183, 37, 122, 14, 124, 65, 67]

    def test_default_queue_totals_and_service_order(self) -> None:
        expected = {
            "FCFS": (640, [98, 183, 37, 122, 14, 124, 65, 67]),
            "SSTF": (236, [65, 67, 37, 14, 98, 122, 124, 183]),
            "SCAN": (331, [65, 67, 98, 122, 124, 183, 37, 14]),
            "C-SCAN": (382, [65, 67, 98, 122, 124, 183, 14, 37]),
            "LOOK": (299, [65, 67, 98, 122, 124, 183, 37, 14]),
            "C-LOOK": (322, [65, 67, 98, 122, 124, 183, 14, 37]),
        }

        for algorithm, (total, service_order) in expected.items():
            with self.subTest(algorithm=algorithm):
                result = simulate(algorithm, self.cylinders, self.head, self.requests)
                self.assertEqual(result.total_movement, total)
                self.assertEqual(list(result.service_order), service_order)

    def test_scan_records_boundary_but_look_does_not(self) -> None:
        scan = simulate("SCAN", 200, 50, [10, 90], "right")
        look = simulate("LOOK", 200, 50, [10, 90], "right")

        self.assertIn(199, scan.path)
        self.assertNotIn(199, look.path)
        self.assertEqual(scan.total_movement, 338)
        self.assertEqual(look.total_movement, 120)

    def test_c_scan_wrap_counts_as_travel_not_service(self) -> None:
        result = simulate("C-SCAN", 200, 50, [10, 90], "right")
        wrap = next(movement for movement in result.movements if movement.kind == "Circular wrap")

        self.assertEqual((wrap.start, wrap.end, wrap.distance), (199, 0, 199))
        self.assertFalse(wrap.serviced)
        self.assertEqual(list(result.service_order), [90, 10])

    def test_leftward_circular_sweeps_use_opposite_boundary(self) -> None:
        c_scan = simulate("C-SCAN", 200, 53, [14, 65], "left")
        c_look = simulate("C-LOOK", 200, 53, [14, 65], "left")
        c_scan_wrap = next(
            movement for movement in c_scan.movements if movement.kind == "Circular wrap"
        )

        self.assertEqual((c_scan_wrap.start, c_scan_wrap.end, c_scan_wrap.distance), (0, 199, 199))
        self.assertEqual(list(c_scan.service_order), [14, 65])
        self.assertEqual(list(c_look.service_order), [14, 65])
        self.assertEqual(c_look.total_movement, 90)
        self.assertNotIn(0, c_look.path)
        self.assertNotIn(199, c_look.path)

    def test_duplicate_requests_are_each_serviced(self) -> None:
        result = simulate("SSTF", 10, 4, [4, 2, 2])

        self.assertEqual(list(result.service_order), [4, 2, 2])
        self.assertEqual(result.total_movement, 2)

    def test_validation_rejects_out_of_range_positions(self) -> None:
        with self.assertRaisesRegex(ValueError, "initial head"):
            simulate("FCFS", 10, 10, [2])
        with self.assertRaisesRegex(ValueError, "Every request"):
            simulate("FCFS", 10, 5, [10])

    def test_sequence_and_input_parsing(self) -> None:
        self.assertEqual(
            parse_integer_list("53, 98 183", "Queue"),
            [53, 98, 183],
        )
        self.assertEqual(
            [move["distance"] for move in calculate_sequence([53, 98, 183, 37, 122])],
            [45, 85, 146, 85],
        )
        with self.assertRaisesRegex(ValueError, "invalid integer"):
            parse_integer_list("53, nope", "Queue")


if __name__ == "__main__":
    unittest.main()
