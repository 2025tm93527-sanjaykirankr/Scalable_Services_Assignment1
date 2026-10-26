"""Build the Assignment 1 design report PDF with ReportLab."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "Assignment1_Design_Report.pdf"
NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#276A8A")
PALE = colors.HexColor("#EDF4F7")
INK = colors.HexColor("#202B35")
MUTED = colors.HexColor("#5E6C76")
GRID = colors.HexColor("#CCD7DE")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=25, leading=30, alignment=TA_LEFT, textColor=colors.black,
    spaceAfter=10,
))
styles.add(ParagraphStyle(
    name="ReportSubtitle", parent=styles["Normal"], fontName="Helvetica",
    fontSize=13, leading=18, textColor=BLUE, spaceAfter=15,
))
styles.add(ParagraphStyle(
    name="Section", parent=styles["Heading1"], fontName="Helvetica-Bold",
    fontSize=16, leading=20, textColor=colors.black, spaceBefore=10, spaceAfter=8,
    keepWithNext=True,
))
styles.add(ParagraphStyle(
    name="Subsection", parent=styles["Heading2"], fontName="Helvetica-Bold",
    fontSize=11.2, leading=14, textColor=colors.black, spaceBefore=6, spaceAfter=4,
    keepWithNext=True,
))
styles.add(ParagraphStyle(
    name="BodySmall", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=8.8, leading=12.2, textColor=INK, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="Body", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=9.4, leading=13.3, textColor=INK, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="Cell", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=7.7, leading=10, textColor=INK, spaceAfter=0,
))
styles.add(ParagraphStyle(
    name="CellHead", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=7.8, leading=10, textColor=colors.white, spaceAfter=0,
))
styles.add(ParagraphStyle(
    name="Caption", parent=styles["BodyText"], fontName="Helvetica-Oblique",
    fontSize=7.6, leading=10, textColor=MUTED, alignment=TA_CENTER,
    spaceBefore=3, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold",
    fontSize=9.2, leading=13, textColor=NAVY, spaceAfter=0,
))


def P(text, style="Body"):
    return Paragraph(text, styles[style])


def table(rows, widths, header=True, repeat=1):
    t = Table(rows, colWidths=widths, repeatRows=repeat if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.45, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), NAVY)]
        if len(rows) > 1:
            commands += [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE])]
    t.setStyle(TableStyle(commands))
    return t


def arrow(c, x1, y1, x2, y2, label="", color=BLUE, label_offset=6):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(1.1)
    c.line(x1, y1, x2, y2)
    angle = 0 if x2 >= x1 else 3.14159
    size = 5
    if angle == 0:
        c.line(x2, y2, x2-size, y2+size/1.7)
        c.line(x2, y2, x2-size, y2-size/1.7)
    else:
        c.line(x2, y2, x2+size, y2+size/1.7)
        c.line(x2, y2, x2+size, y2-size/1.7)
    if label:
        c.setFont("Helvetica", 6.6)
        c.setFillColor(INK)
        c.drawCentredString((x1+x2)/2, y1+label_offset, label)


class ArchitectureDiagram(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = 520, 180

    def wrap(self, aw, ah):
        return min(self.width, aw), self.height

    def draw(self):
        c = self.canv
        # Client and orchestrator sit above a clearly separated downstream row.
        for x, y, w, h, title, detail in [
            (18, 138, 82, 34, "API client", "caller"),
            (216, 138, 88, 34, "Booking", "port 8000"),
        ]:
            c.setFillColor(PALE if title != "Booking" else colors.HexColor("#DCEAF1"))
            c.setStrokeColor(BLUE)
            c.roundRect(x, y, w, h, 6, fill=1, stroke=1)
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(x+w/2, y+20, title)
            c.setFont("Helvetica", 7)
            c.drawCentredString(x+w/2, y+8, detail)
        arrow(c, 100, 155, 215, 155, "REST: booking")
        c.setStrokeColor(GRID)
        c.setDash(2, 2)
        c.line(304, 155, 344, 155)
        c.setDash()
        c.setFillColor(colors.white)
        c.setStrokeColor(GRID)
        c.roundRect(344, 138, 96, 34, 5, fill=1, stroke=1)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7)
        c.drawCentredString(392, 151, "booking.db")
        c.setFont("Helvetica-Oblique", 6)
        c.drawCentredString(324, 159, "owns")

        # Booking branches to the three independently owned services.
        centers = [80, 260, 440]
        c.setStrokeColor(BLUE)
        c.setLineWidth(1.1)
        c.line(260, 138, 260, 114)
        c.line(80, 114, 440, 114)
        labels = ["REST: reserve / release", "REST: charge + retry", "REST: notification"]
        names = [("Inventory", "port 8001", "inventory.db"),
                 ("Payment mock", "port 8002", "payment.db"),
                 ("Notification", "port 8003", "notification.db")]
        for center, label, (name, port, db) in zip(centers, labels, names):
            c.setFillColor(INK)
            c.setFont("Helvetica", 6.6)
            c.drawCentredString(center, 101, label)
            c.line(center, 114, center, 82)
            c.line(center, 82, center-4, 88)
            c.line(center, 82, center+4, 88)
            x = center-62
            c.setFillColor(PALE)
            c.setStrokeColor(BLUE)
            c.roundRect(x, 47, 124, 35, 5, fill=1, stroke=1)
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 7.7)
            c.drawCentredString(center, 67, name)
            c.setFont("Helvetica", 6.8)
            c.drawCentredString(center, 55, port)
            c.setStrokeColor(GRID)
            c.setFillColor(colors.white)
            c.roundRect(center-43, 12, 86, 23, 4, fill=1, stroke=1)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 6.8)
            c.drawCentredString(center, 21, db)
            c.setStrokeColor(GRID)
            c.setDash(2, 2)
            c.line(center, 47, center, 35)
            c.setDash()
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 6.8)
        c.drawCentredString(260, 2, "Each service owns its database; cross-service references are IDs only.")


class SequenceDiagram(Flowable):
    def __init__(self, failure=False):
        super().__init__()
        self.failure = failure
        self.width, self.height = 520, 184 if failure else 150

    def wrap(self, aw, ah):
        return min(self.width, aw), self.height

    def draw(self):
        c = self.canv
        participants = [(35, "Client"), (140, "Booking"), (255, "Inventory"), (365, "Payment"), (475, "Notify")]
        top, bottom = self.height-28, 12
        for x, name in participants:
            c.setFillColor(PALE)
            c.setStrokeColor(GRID)
            c.roundRect(x-29, top, 58, 22, 4, fill=1, stroke=1)
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(x, top+8, name)
            c.setStrokeColor(GRID)
            c.setDash(2, 2)
            c.line(x, top, x, bottom)
            c.setDash()
        if not self.failure:
            msgs = [
                (35, 140, "POST booking + key"),
                (140, 255, "reserve slot"),
                (255, 140, "reserved"),
                (140, 365, "charge (stable key)"),
                (365, 140, "charged"),
                (140, 475, "record notification"),
                (140, 35, "201 confirmed"),
            ]
        else:
            msgs = [
                (35, 140, "POST booking + key"),
                (140, 255, "reserve slot"),
                (255, 140, "reserved"),
                (140, 365, "charge, retry x3"),
                (365, 140, "unavailable"),
                (140, 255, "release reservation"),
                (140, 35, "503 payment failed"),
            ]
        gap = (top-12)/(len(msgs)+1)
        for i, (x1, x2, label) in enumerate(msgs):
            y = top-11-(i+1)*gap
            if x1 > x2:
                c.setDash(3, 2)
                arrow(c, x1, y, x2, y, label, color=MUTED)
                c.setDash()
            else:
                arrow(c, x1, y, x2, y, label)


class ERDiagram(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = 520, 190

    def wrap(self, aw, ah):
        return min(self.width, aw), self.height

    def draw(self):
        c = self.canv
        cards = [
            ("Booking DB", ["bookings", "booking_id PK", "customer_id", "slot_id", "amount, status", "payment_id", "idempotency", "idem_key PK", "fingerprint", "status_code", "response_json"]),
            ("Inventory DB", ["slots", "slot_id PK", "capacity", "remaining", "reservations", "reservation_id PK", "slot_id", "booking_id UNIQUE", "status"]),
            ("Payment DB", ["payments", "payment_id PK", "idempotency_key UNIQUE", "fingerprint", "booking_id", "amount, status"]),
            ("Notification DB", ["notifications", "notification_id PK", "booking_id UNIQUE", "customer_id", "message"]),
        ]
        x_positions = [3, 134, 265, 396]
        card_w = 122
        for (title, lines), x in zip(cards, x_positions):
            c.setFillColor(PALE)
            c.setStrokeColor(GRID)
            c.roundRect(x, 27, card_w, 151, 5, fill=1, stroke=1)
            c.setFillColor(NAVY)
            c.rect(x, 158, card_w, 20, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(x+card_w/2, 165, title)
            y = 148
            for line in lines:
                c.setFillColor(INK if "PK" in line or "UNIQUE" in line else MUTED)
                c.setFont("Helvetica-Bold" if line in {"bookings", "idempotency", "slots", "reservations", "payments", "notifications"} else "Helvetica", 6.7)
                c.drawString(x+7, y, line)
                y -= 11
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 7)
        c.drawCentredString(260, 11, "IDs cross service boundaries; the databases have no cross-service foreign keys or joins.")


class NumberedCanvas:
    """Canvas factory wrapper is attached below as a Canvas subclass."""


from reportlab.pdfgen import canvas as pdfcanvas


class NumberedCanvasImpl(pdfcanvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            page = self._pageNumber
            if page > 1:
                self.setStrokeColor(GRID)
                self.line(18*mm, 13*mm, A4[0]-18*mm, 13*mm)
                self.setFont("Helvetica", 7)
                self.setFillColor(MUTED)
                self.drawString(18*mm, 8*mm, "Scalable Services | Assignment 1")
            self.setFont("Helvetica", 7)
            self.setFillColor(MUTED)
            self.drawRightString(A4[0]-18*mm, 8*mm, f"{page} / {total}")
            if page > 1:
                self.setFont("Helvetica-Bold", 7)
                self.setFillColor(NAVY)
                self.drawString(18*mm, A4[1]-10*mm, "APPOINTMENT BOOKING MICROSERVICES")
            pdfcanvas.Canvas.showPage(self)
        pdfcanvas.Canvas.save(self)


def bullet(text):
    return P(f"<font color='{BLUE.hexval()}'><b>-</b></font> {text}", "BodySmall")


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm,
        topMargin=19*mm, bottomMargin=19*mm,
        title="Appointment Booking Microservices Design Report",
        author="Assignment 1 team",
        subject="Scalable Services SEZG583, Assignment 1",
    )
    story = []
    story += [Spacer(1, 21*mm), P("Assignment 1 Design and Development", "ReportTitle"),
              P("Appointment Booking Microservices", "ReportSubtitle"),
              P("Scalable Services (SEZG583) | MTech | 13 marks", "Body"),
              Spacer(1, 5*mm)]
    cover = [
        [P("Submission details", "CellHead"), P("Current information", "CellHead")],
        [P("Application", "Cell"), P("Appointment booking using four independently runnable Python and FastAPI services", "Cell")],
        [P("Team", "Cell"), P("Group 8; primary contributor: Sanjay Kiran K R (2025TM93527)", "Cell")],
        [P("Repository", "Cell"), P('<link href="https://github.com/2025tm93527-sanjaykirankr/Scalable_Services_Assignment1">Scalable_Services_Assignment1</link><br/>https://github.com/2025tm93527-sanjaykirankr/Scalable_Services_Assignment1', "Cell")],
        [P("Demo video", "Cell"), P("[Add Google Drive link to the 8-10 minute video]", "Cell")],
        [P("Report date", "Cell"), P("27 October 2026", "Cell")],
    ]
    story += [table(cover, [41*mm, 132*mm]), Spacer(1, 8*mm),
              P("Report status", "Subsection"),
              P("This report records the implementation and locally captured run results in the repository. Group 8 and its primary contributor are identified. The individual reflection and demo video link remain to be completed by the student and team.", "Body"),
              Spacer(1, 4*mm),
              P("The application demonstrates a booking transaction across inventory, payment, and notification services. The evidence runs show capacity protection, replay safety, compensation after a payment outage, and a successful end-to-end booking.", "Callout"),
              PageBreak()]

    story += [P("1. Problem and scope", "Section"),
              P("The application books limited-capacity appointment slots. A client asks the Booking service to reserve a slot, charge a simulated payment, and record a notification. The design is intended to demonstrate service ownership and correct behavior when requests compete, repeat, or encounter a downstream failure.", "Body"),
              P("Assumptions and scope", "Subsection"),
              bullet("Each slot has a finite capacity. Inventory owns the capacity and reservation state."),
              bullet("The Booking service coordinates the workflow synchronously over REST. Payment and notification are educational mocks; no real payment or message is sent."),
              bullet("Authentication, user interface, real payment integration, and production deployment are out of scope."),
              bullet("SQLite keeps local setup small. The report treats the implementation as a teaching demo, not a high-throughput production deployment."),
              P("Business rules", "Subsection")]
    rules = [
        [P("ID", "CellHead"), P("Rule", "CellHead"), P("Implementation and test", "CellHead")],
        [P("BR1", "Cell"), P("A slot cannot be over-allocated; remaining capacity must not become negative.", "Cell"), P("Inventory uses an atomic conditional update. Test: `test_br1_inventory_never_overallocates_last_slot`; concurrency evidence: 20 parallel calls.", "Cell")],
        [P("BR2", "Cell"), P("A booking needs customer ID, slot ID, positive amount, and an Idempotency-Key.", "Cell"), P("Pydantic validation and required-header check. Test: `test_br2_requires_valid_fields_positive_amount_and_idempotency_key`.", "Cell")],
        [P("BR3", "Cell"), P("Same key and same payload replay the saved result; a changed payload using that key is rejected.", "Cell"), P("Canonical fingerprint and stored response. Test: `test_br3_same_key_replays_one_result_and_changed_payload_conflicts`; Challenge 2 evidence also covers simultaneous calls.", "Cell")],
        [P("BR4", "Cell"), P("When payment fails after reservation, Booking attempts to release the reservation.", "Cell"), P("Booking requests Inventory compensation. Test: `test_br4_payment_failure_releases_inventory_reservation`; Challenge 3A outage run.", "Cell")],
        [P("BR5", "Cell"), P("A notification is attempted only after payment succeeds.", "Cell"), P("Booking invokes notification after a successful charge. Test: `test_br5_notification_is_attempted_only_after_successful_payment`.", "Cell")],
    ]
    story += [table(rules, [13*mm, 68*mm, 92*mm]), PageBreak()]

    story += [P("2. Service decomposition", "Section"),
              P("The boundaries follow business capabilities. Booking owns the workflow and booking records; Inventory owns slot capacity; Payment and Notification own their mock records. No service queries another service's SQLite database.", "Body")]
    services = [
        [P("Service", "CellHead"), P("Responsibility", "CellHead"), P("Owned data", "CellHead"), P("Port", "CellHead")],
        [P("Booking", "Cell"), P("Coordinates reserve, charge, notification, replay, and compensation.", "Cell"), P("Bookings and idempotency responses.", "Cell"), P("8000", "Cell")],
        [P("Inventory", "Cell"), P("Atomically reserves or releases appointment capacity.", "Cell"), P("Slots and reservations.", "Cell"), P("8001", "Cell")],
        [P("Payment mock", "Cell"), P("Records simulated charges and deduplicates charge keys; can be stopped or configured to fail.", "Cell"), P("Payments.", "Cell"), P("8002", "Cell")],
        [P("Notification mock", "Cell"), P("Records a simulated post-payment notification.", "Cell"), P("Notifications.", "Cell"), P("8003", "Cell")],
    ]
    story += [table(services, [28*mm, 68*mm, 57*mm, 20*mm]),
              P("Why these boundaries", "Subsection"),
              P("Inventory changes capacity independently of booking orchestration. Payment and notification are external-style dependencies with their own data and failure modes. Booking owns the transaction sequence because it must coordinate the reservation, charge, notification, and compensation. The design avoids four generic database wrappers by placing actual business rules in the services.", "Body"),
              P("Alternative considered", "Subsection"),
              P("A single application and database would make atomic transactions simpler, but it would not demonstrate database-per-service ownership or independent failure. Splitting each table into its own service would add calls without a distinct business responsibility. The selected four-service split is based on the appointment workflow and its independent dependencies.", "Body"),
              PageBreak()]

    story += [P("3. Architecture and transaction sequences", "Section"),
              P("The services communicate over REST and pass X-Request-ID between downstream calls. FastAPI provides a per-service OpenAPI document at `/openapi.json` and interactive documentation at `/docs`.", "Body"),
              ArchitectureDiagram(), P("Figure 1. Service components, REST calls, and separate data stores.", "Caption"),
              P("Happy path", "Subsection"), SequenceDiagram(False),
              P("Figure 2. Successful booking: reserve, charge, notify, and confirm.", "Caption"),
              P("Payment failure path", "Subsection"), SequenceDiagram(True),
              P("Figure 3. After bounded payment retries fail, Booking attempts to release the reserved slot and returns HTTP 503.", "Caption"),
              PageBreak()]

    story += [P("4. Data design and ownership", "Section"),
              P("Each service owns its SQLite database. Cross-service associations use IDs in payloads; there are no cross-database joins or foreign keys. Each database can be replaced independently, subject to the workflow's need to reconcile partial failures.", "Body"),
              ERDiagram(), P("Figure 4. Per-service entity relationships. PK and UNIQUE identify local constraints; cross-service IDs are not foreign keys.", "Caption"),
              P("Ownership notes", "Subsection"),
              bullet("Booking stores the request fingerprint and the response associated with an idempotency key."),
              bullet("Inventory stores local slot capacity and reservation status. Its SQL update only decrements a positive remaining value."),
              bullet("Payment stores a unique idempotency key and payload fingerprint for each mock charge."),
              bullet("Notification stores one record per booking ID, using a local uniqueness constraint to avoid duplicate records."),
              P("The local SQLite files are for development and evidence runs. Production deployment would require managed database configuration, credentials, backups, and concurrency controls appropriate to multiple service instances.", "Body"),
              PageBreak()]

    story += [P("5. API design", "Section"),
              P("All business endpoints are versioned under `/api/v1`. FastAPI validates request bodies and publishes OpenAPI. The main booking endpoint requires the `Idempotency-Key` header; booking propagates the request ID to downstream calls.", "Body")]
    apis = [
        [P("Service", "CellHead"), P("Method and path", "CellHead"), P("Purpose and key result", "CellHead")],
        [P("Booking", "Cell"), P("POST `/api/v1/bookings`", "Cell"), P("Create or replay a booking; 201 on confirmation, 409 for key/payload conflict, 503 on payment failure.", "Cell")],
        [P("Booking", "Cell"), P("GET `/api/v1/bookings/{booking_id}`", "Cell"), P("Read a booking; 200 or 404.", "Cell")],
        [P("Inventory", "Cell"), P("GET `/api/v1/slots`", "Cell"), P("List slot capacity and remaining units.", "Cell")],
        [P("Inventory", "Cell"), P("POST `/api/v1/slots/{slot_id}/reserve`", "Cell"), P("Reserve one unit; 409 when full, 404 for unknown slot.", "Cell")],
        [P("Inventory", "Cell"), P("POST `/api/v1/slots/{slot_id}/release`", "Cell"), P("Compensate a reservation after payment failure.", "Cell")],
        [P("Payment mock", "Cell"), P("POST `/api/v1/payments/charge`", "Cell"), P("Record or replay a simulated charge; supports a failure mode.", "Cell")],
        [P("Notification mock", "Cell"), P("POST `/api/v1/notifications`", "Cell"), P("Record a notification after successful payment.", "Cell")],
        [P("All services", "Cell"), P("GET `/health`; GET `/openapi.json`; GET `/docs`", "Cell"), P("Health and generated API documentation for each service.", "Cell")],
    ]
    story += [table(apis, [25*mm, 73*mm, 75*mm]),
              P("Example request", "Subsection"),
              P('`POST http://127.0.0.1:8000/api/v1/bookings` with `Idempotency-Key: demo-001` and JSON body `{"customer_id":"cust-1","slot_id":"slot-1","amount":25.00}`. A confirmed response includes booking, reservation, and payment IDs plus notification status.', "BodySmall"),
              P("Error model", "Subsection"),
              P("Application errors use a JSON envelope containing `error.code`, `error.message`, and `error.request_id`. FastAPI request-validation failures use FastAPI's standard validation response, so validation errors are not fully normalized to the shared error envelope yet.", "Body"),
              P("OpenAPI endpoints", "Subsection"),
              bullet("Booking: `http://127.0.0.1:8000/openapi.json`"),
              bullet("Inventory: `http://127.0.0.1:8001/openapi.json`"),
              bullet("Payment mock: `http://127.0.0.1:8002/openapi.json`"),
              bullet("Notification mock: `http://127.0.0.1:8003/openapi.json`"),
              PageBreak()]

    story += [P("6. Engineering challenges and evidence", "Section"),
              P("Challenge 1: concurrency control", "Subsection"),
              P("Inventory executes `UPDATE slots SET remaining=remaining-1 WHERE slot_id=? AND remaining>0` inside a write transaction. This makes the decrement conditional at the database boundary. A plain application-level check followed by a later update can let multiple requests observe the same final unit before a write occurs.", "BodySmall"),
              bullet("Recorded run: 20 parallel requests against `slot-2` with capacity 1; exactly 1 HTTP 201 and 19 HTTP 409 responses."),
              bullet("Final database check: capacity 1, remaining 0, one active reservation."),
              bullet("Evidence files: `evidence/challenge-1-concurrency/concurrency-run.txt`, `final-database-state.txt`, and `inventory-service.log`."),
              P("Challenge 2: idempotency", "Subsection"),
              P("Booking stores a canonical JSON fingerprint, HTTP status, and serialized response under a unique idempotency key. SQLite `BEGIN IMMEDIATE` serializes concurrent duplicate-key handling in this demo. A changed payload with an existing key returns HTTP 409. The payment mock also stores unique charge keys.", "BodySmall"),
              bullet("Sequential exact replay returned the same response and `Idempotency-Replayed: true`; the changed payload returned 409."),
              bullet("Twenty simultaneous identical requests returned one identical booking result; one request performed the work and 19 responses were marked as replays."),
              bullet("The run used two distinct keys and recorded two bookings, reservations, payments, and notifications total, one per key."),
              bullet("Evidence files: `evidence/challenge-2-idempotency/idempotency-run.txt`, `booking-service.log`, and `database-record-counts.json`."),
              P("Challenge 3A: resilience", "Subsection"),
              P("The selected optional challenge uses a one-second downstream timeout, three total payment attempts, exponential backoff, and jitter. On persistent failure, Booking attempts a compensating inventory release and returns HTTP 503. The payment key is derived from the booking ID so retries for one booking use the same key.", "BodySmall"),
              bullet("With payment stopped, the request returned 503 after two retry delays; the booking was stored as FAILED."),
              bullet("After compensation, the reservation was RELEASED and slot capacity returned to 5. After payment restarted, a new key succeeded with HTTP 201 and one payment record."),
              bullet("Evidence files: `evidence/challenge-3a-resilience/resilience-run.txt`, `booking-service.log`, and `database-states.json`."),
              P("All run outputs are local evidence, not a claim of production load capacity. Screenshots of the commands and outputs still need to be added to the evidence folders.", "BodySmall"),
              PageBreak()]

    story += [P("7. Testing and results", "Section"),
              P("Business-rule tests use Python's standard-library `unittest` runner and isolated SQLite databases. The end-to-end script exercises the live service process chain and verifies persisted records in each database.", "Body"),
              table([
                  [P("Test", "CellHead"), P("Observed result", "CellHead"), P("Evidence", "CellHead")],
                  [P("BR1-BR5 unit tests", "Cell"), P("5 tests passed; capacity, validation, replay/conflict, compensation, and notification ordering covered.", "Cell"), P("`evidence/tests/business-rule-tests.txt`", "Cell")],
                  [P("Main transaction E2E", "Cell"), P("Create booking returned 201; retrieve returned 200; one confirmed booking, reservation, payment, and notification were present.", "Cell"), P("`evidence/tests/e2e-run.txt` and database checks JSON", "Cell")],
                  [P("Concurrency challenge", "Cell"), P("1 success and 19 rejections; final slot state consistent.", "Cell"), P("`evidence/challenge-1-concurrency/`", "Cell")],
                  [P("Idempotency challenge", "Cell"), P("Exact replay, changed-payload conflict, and 20 simultaneous duplicates verified.", "Cell"), P("`evidence/challenge-2-idempotency/`", "Cell")],
                  [P("Resilience challenge", "Cell"), P("Payment outage retried and failed gracefully; reservation released; recovery succeeded.", "Cell"), P("`evidence/challenge-3a-resilience/`", "Cell")],
              ], [37*mm, 91*mm, 45*mm]),
              P("Test command", "Subsection"),
              P("From the project root: `python -m unittest discover -s tests -p test_business_rules.py -v`. Install the booking and inventory service requirements and `tests/requirements.txt` first. The current evidence includes raw text logs and database checks; screenshot evidence remains to be captured.", "Body"),
              PageBreak()]

    story += [P("8. Design decisions and trade-offs", "Section"),
              table([
                  [P("Decision", "CellHead"), P("Options considered", "CellHead"), P("Choice and rationale", "CellHead"), P("Trade-off", "CellHead")],
                  [P("REST versus broker", "Cell"), P("Synchronous REST or asynchronous broker events.", "Cell"), P("REST keeps the classroom flow visible in API calls and satisfies the assignment. Each service exposes a direct HTTP contract.", "Cell"), P("The booking path depends on downstream availability and has a synchronous chain.", "Cell")],
                  [P("Orchestration versus choreography", "Cell"), P("Booking coordinates steps or services react to events.", "Cell"), P("Booking orchestration makes reserve, charge, notify, and compensation order explicit and easy to trace.", "Cell"), P("Workflow logic is concentrated in Booking; partial failure still requires reconciliation.", "Cell")],
                  [P("SQLite versus server database", "Cell"), P("Local SQLite or a managed relational database.", "Cell"), P("SQLite reduces setup friction and supports atomic conditional updates for the demo.", "Cell"), P("A shared-file SQLite database is not suitable for multi-instance production scale or operational resilience.", "Cell")],
                  [P("Compensation versus distributed transaction", "Cell"), P("Attempt release after payment failure or require distributed transaction coordination.", "Cell"), P("Compensation avoids claiming cross-service ACID behavior and demonstrates a saga-like action.", "Cell"), P("The compensation can fail, and a process crash can leave an intermediate state.", "Cell")],
              ], [31*mm, 45*mm, 61*mm, 36*mm]),
              P("9. Limitations and future work", "Section"),
              bullet("The booking service holds a local SQLite write transaction while calling downstream services. This serializes same-key requests but harms throughput and should be replaced by durable workflow state for production."),
              bullet("The services cannot share a distributed ACID transaction. A crash between reservation, charge, and local persistence can require reconciliation."),
              bullet("Notification is best-effort after payment and has no outbox or retry worker."),
              bullet("Authentication, production observability, deployment, and operational secrets management are out of scope. Configure per-service credentials and database services before a production rollout."),
              bullet("The current SQLite files are separate but do not have separate database credentials. The Uvicorn ports are supplied on the startup command rather than read from an application port environment variable; both are gaps against the assignment's operability checklist."),
              bullet("A fresh clone has not yet been verified from the README, and the repository URL is not available in this workspace."),
              bullet("Future work includes explicit booking states, durable saga/outbox processing, metrics and tracing, and a server database with managed backups and access control."),
              P("10. Submission links", "Section"),
              P('GitHub repository: <link href="https://github.com/2025tm93527-sanjaykirankr/Scalable_Services_Assignment1">Scalable_Services_Assignment1</link> (https://github.com/2025tm93527-sanjaykirankr/Scalable_Services_Assignment1). Google Drive folder containing the video and other documents: [Add link]. Demo video: [Add 8-10 minute recording link].', "Body"),
              PageBreak()]

    story += [P("Appendix A. Team contributions", "Section"),
              P("This version lists the primary contributor only, as requested. Confirm whether the course requires every Group 8 member to appear in this table before submission.", "Body"),
              table([
                  [P("Member", "CellHead"), P("Owned work", "CellHead"), P("Evidence (commits, files, demo)", "CellHead")],
                  [P("Sanjay Kiran K R (2025TM93527)", "Cell"), P("Major contribution: project coordination, service design and integration oversight, test and evidence review, and report finalization.", "Cell"), P("Repository review, challenge and test evidence, report. AI assistance is disclosed in Appendix C.", "Cell")],
              ], [35*mm, 77*mm, 61*mm]),
              P("Appendix B. Individual reflections", "Section"),
              P("Each student should add an individual half-page reflection describing what they built, the hardest problem they solved, and what they would change. These personal statements are intentionally not fabricated here.", "Body"),
              P("Sanjay Kiran K R (2025TM93527) - [Add your half-page reflection: what you built, the hardest problem solved, and what you would change.]", "BodySmall"),
              P("Appendix C. AI-use declaration", "Section"),
              P("During preparation of this report and evidence package, OpenAI ChatGPT/Codex was used to review the assignment brief and repository, help add business-rule tests, create repeatable evidence-runner scripts, execute local checks, and draft report text. The team must review the generated material, ensure it understands and can explain the code, and add any AI tools used by team members for other work. The team remains responsible for the final submission and its accuracy.", "Body"),
              P("Appendix D. Evidence index", "Section"),
              bullet("Concurrency: `evidence/challenge-1-concurrency/README.md`."),
              bullet("Idempotency: `evidence/challenge-2-idempotency/README.md`."),
              bullet("Resilience 3A: `evidence/challenge-3a-resilience/README.md`."),
              bullet("Unit and end-to-end tests: `evidence/tests/README.md`."),
              P("Add the required timestamped screenshots to each evidence folder after capture.", "BodySmall")]

    doc.build(story, canvasmaker=NumberedCanvasImpl)
    print(f"Created {OUT}")


if __name__ == "__main__":
    main()
