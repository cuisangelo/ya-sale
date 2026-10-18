from app.legs.domain import normalize_place
from app.reader.domain import OperatorSite


def _places(*names: str) -> frozenset[str]:
    return frozenset(normalize_place(name) for name in names)


# An operator joins only after its terms and robots.txt were read; the note records what they say.
OPERATORS = (
    OperatorSite(
        domain="turismodias.com.pe",
        name="Turismo Días",
        start_url="https://www.turismodias.com.pe/",
        # The origin list their own search offers.
        serves=_places(
            "Cajamarca", "Chepén", "Chiclayo", "Chilete", "Chimbote", "Ciudad de Dios", "Jaén", "Lima", "Moyobamba",
            "Nueva Cajamarca", "Pacasmayo", "Piura", "Sullana", "Tarapoto", "Tembladera", "Trujillo",
        ),
        compliance_note="robots.txt: 'User-agent: * Allow: /'. Terms (/terms) cover passenger conditions only and say "
        "nothing on automated access or data extraction. Read only, stops at the departures list.",
    ),
    OperatorSite(
        domain="movilbus.pe",
        name="Movil Bus",
        start_url="https://www.movilbus.pe/",
        # Their "Rutas frecuentes" footer plus Huancayo, whose list the reader read.
        serves=_places(
            "Lima", "Huancayo", "Huaraz", "Chiclayo", "Tarapoto", "Barranca", "Ayacucho", "Moyobamba", "Jaén", "Casma",
            "Bagua Grande", "Juanjuí", "Rioja", "Villa Rica", "Oxapampa", "La Merced",
        ),
        compliance_note="robots.txt: 'User-agent: * Allow: /'. Travel clauses (/clausulas-de-viaje) and the policies PDF "
        "say nothing on automated access or data extraction. Public UI only, as a visitor clicks it: no API calls, "
        "no tokens from their scripts. Read only, stops at step 1 (Destino y fecha).",
    ),
)

BY_DOMAIN = {site.domain: site for site in OPERATORS}
