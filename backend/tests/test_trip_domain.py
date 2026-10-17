from app.trips.domain import PlannedHop


def test_alternatives_drop_the_main_mode_and_repeats():
    hop = PlannedHop.of("Lima", "Tarapoto", "bus", ["bus", "avion", "avion"])
    assert hop.modes == ("bus", "avion")


def test_a_hop_keeps_at_most_two_modes():
    assert PlannedHop.of("Lima", "Tarapoto", "bus", ["avion", "colectivo"]).modes == ("bus", "avion")
