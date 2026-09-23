# Gold question set — 25 questions

Human-readable companion to `eval/data/gold.jsonl`. Same 25 entries, with the full
answer and the source anchor spelled out. The harness reads the `.jsonl`; this
file is for review and for the AS8.2 technical documentation.

## How to read the citations

`page` is the **1-based PDF page index** — what the parser reports and what
`bbox` and `source_image` are relative to. It is *not* always the number
printed on the page. The ACS580 firmware manual runs an offset of 2 (PDF 553
prints "555"); the hardware manuals run an offset of 0. Cross-references
inside the manual text use the printed number, so both are stored.

Getting this wrong is a silent recall@5 killer: retrieval would be working
correctly and scoring zero.

## Composition

| Query type | Count |
|---|---|
| `prose` | 6 |
| `table` | 7 |
| `diagram` | 6 |
| `fault_code` | 6 |
| **Total** | **25** |

`cross_manual` is carried as a boolean flag rather than a sixth type, so the
four types still sum to 25 and the harness can print a cross-cutting
`cross_manual` row over the flagged entries. 3 entries are flagged
(G10, G11, G25). If you would rather it be a fifth `query_type`, re-tag those
three — nothing else depends on the choice.

`scan_target: true` marks the 3 entries (G10, G11, G24) whose answers exist
only in `acs550_to_acs580_replacement.pdf`, the document nominated to become
the scanned manual. See `corpus.md` — that requirement is still open.

Verify every citation at any time:

```bash
python tools/verify_gold.py
```

It opens each cited page and checks the answer's content words are actually
there. Currently 25/25. Non-zero exit on any failure, so it can gate a commit.

---

## fault_code (6)

### G01 — "ACS580 is showing fault 2330. What is it and what should I check first?"
**Answer.** 2330 is *Earth leakage*. The drive has detected a load unbalance,
typically caused by an earth fault in the motor or the motor cable. The manual
orders the checks: first confirm there are no power factor correction
capacitors or surge absorbers in the motor cable; then look for an earth fault
by measuring the insulation resistance of the motor and motor cable; then, if
allowed, try running the motor in scalar control mode (parameter 99.04 *Motor
control mode*). If no earth fault can be found, contact ABB.
**Source.** `acs580_firmware_manual` PDF p553 (printed 555), *Fault tracing*.

### G02 — "What causes fault 2381 IGBT overload and how do I clear it?"
**Answer.** Excessive IGBT junction-to-case temperature. The fault protects the
IGBTs and can be triggered by a short circuit in the motor cable. Checks:
motor cable, ambient conditions, air flow and fan operation, heatsink fins for
dust pick-up, and motor power against drive power.
**Source.** `acs580_firmware_manual` PDF p553 (printed 555), *Fault tracing*.

### G03 — "Drive trips on 3220. What does DC link undervoltage mean?"
**Answer.** Intermediate circuit DC voltage is not sufficient, because of a
missing supply phase, a blown fuse, or a fault in the rectifier bridge. Check
supply cabling, fuses and switchgear.
**Source.** `acs580_firmware_manual` PDF p554 (printed 556), *Fault tracing*.

### G04 — "Fault 3385 autophasing failed on a permanent magnet motor. What now?"
**Answer.** The autophasing routine has failed. Try other autophasing modes
(parameter 21.13 *Autophasing mode*); confirm the motor ID run completed
successfully; confirm the motor is not already turning when autophasing
starts; and check that parameter 99.03 *Motor type* is set to *Permanent
magnet motor*. Auxiliary code 0002 specifically means the motor was rotating
during autophasing.
**Source.** `acs580_firmware_manual` PDF p554 (printed 556), *Fault tracing*.

### G05 — "What is fault 7122 and which parameters tune it?"
**Answer.** *Motor overload* — continuous average motor current is above the
defined motor nominal current. Check that motor rotation is not obstructed;
consider that the motor's nominal torque may not be adequate for the
application; and adjust the motor overload parameters 35.51…35.53 and
35.55…35.56.
**Source.** `acs580_firmware_manual` PDF p560 (printed 562), *Fault tracing*.

### G06 — "Getting fault 7181 brake resistor on an ACS580."
**Answer.** Brake resistor broken or not connected. Check that a brake
resistor has actually been connected, check its condition, and check its
dimensioning.
**Source.** `acs580_firmware_manual` PDF p560 (printed 562), *Fault tracing*.

---

## table (7)

### G07 — "Tightening torque for the PE ground lug on an ACS580-01 frame R1?"
**Answer.** 4.0 N·m (2.9 lbf·ft). The same ground lug serves frames R1, R2 and
R3. Maximum PE wire size is 2.5/2.5 mm² (14 AWG, solid/stranded). Note the
table's own caveat: the minimum specified wire size does not necessarily have
sufficient current carrying capacity at maximum load, and the maximum number
of conductors per terminal is 1 except where indicated.
**Source.** `acs580_01_type4x_quickstart` PDF p13, *Terminal data for power
connections*.
**Why it is a good test.** The answer is one cell of a multi-level header
table. A 500-character blind chunk flattens the header away and the number
becomes unattributable — exactly the baseline failure M2 is meant to expose.

### G08 — "How much do I derate an ACS580 at 2500 m altitude?"
**Answer.** Between 1000 m and 4000 m the derating is 1% for every 100 m above
1000 m. At 2500 m that is 15 percentage points, giving a derating factor
k = 0.85 applied to the current in the rating table. Above 2000 m there are
special considerations for corner-grounded installations — contact ABB.
**Source.** `acs580_01_hardware_manual` PDF p310 (printed 310), *Technical
data — Altitude derating*.

### G09 — "Can I recover derating if my cabinet runs cooler than 40 °C?"
**Answer.** Yes. Below +40 °C the derating can be reduced by 1.5 percentage
points for every 1 °C of reduction. The manual's worked example: at 30 °C the
derating factor is 1 − 1.5% × 10 = 0.85. For a more accurate figure ABB points
at the DriveSize PC tool.
**Source.** `acs580_01_hardware_manual` PDF p310 (printed 310), *Technical
data — Altitude derating*.

### G10 — "Swapping an ACS550 frame R6 for an ACS580. Does my cable still fit?" ⟂ cross-manual · scan target
**Answer.** Not at the top end. ACS550 R6 accepts up to 350 MCM stranded;
ACS580 R6 accepts only up to 300 MCM. A cable sized at the ACS550 maximum will
not land in the ACS580 terminal.
**Source.** `acs550_to_acs580_replacement` PDF p16, *Cable sizes and power
loss data*.

### G11 — "On frame R1, how does max cable size compare between ACS550 and ACS580?" ⟂ cross-manual · scan target
**Answer.** It moves the other way on R1: ACS550 R1 takes up to 8 AWG
stranded, ACS580 R1 takes up to 10 AWG — the newer drive accepts a *smaller*
maximum conductor on this frame.
**Source.** `acs550_to_acs580_replacement` PDF p16, *Cable sizes and power
loss data*.
**Why it is a good test.** G10 and G11 point at the same table and the same
page but have opposite answers. A retriever that returns the right page still
has to read the right row, which is what citation accuracy measures.

### G12 — "Contact rating of the relay outputs on an ACS880-01 control unit?"
**Answer.** 250 V AC / 30 V DC, 2 A, on each of the three relay outputs
XRO1, XRO2 and XRO3.
**Source.** `acs880_01_hardware_manual` PDF p186 (printed 186), *Control unit
— relay outputs*.

### G13 — "Which warning code corresponds to fault 2310 overcurrent?"
**Answer.** Warning A2B1 maps to fault 2310 *Overcurrent*: the output current
is more than the internal limit, which can also be caused by an earth fault or
phase loss.
**Source.** `acs580_01_type4x_quickstart` PDF p11, *Warnings and faults*.
**Why it is a good test.** The warning/fault pairing only exists as adjacent
columns in one table. Retrieval has to preserve row structure or the mapping
is lost.

---

## diagram (6)

These six carry their answer in the page graphic. The text layer holds the
terminal labels but not the wiring, so they exercise the AS1.3 vision
description path. A `figure` chunk whose text reads "a wiring diagram" fails
all six.

### G14 — "Which terminal supplies the 10 V reference for a speed potentiometer?"
**Answer.** Terminal 4 on connector X1, labelled **+10V**, is the 10 V DC
reference. The potentiometer wiper returns to terminal 2 (AI1, output
frequency reference 0…10 V) and its low side to terminal 3 (AGND). The diagram
shows a 1…10 kΩ pot.
**Source.** `acs580_01_hardware_manual` PDF p238 (printed 238), *Default
control connection diagram* (ABB Standard macro, CCU-23, frames R1…R5).

### G15 — "What is terminal 1 on the ACS580 X1 connector used for?"
**Answer.** Terminal **SCR**, position 1 on X1, is the signal cable shield
(screen) termination.
**Source.** `acs580_01_hardware_manual` PDF p238 (printed 238), *Default
control connection diagram*.

### G16 — "Default functions of the three relay outputs on an ACS880-01?"
**Answer.** XRO1 = *Ready run*, XRO2 = *Running*, XRO3 = *Fault (-1)*. Each is
wired NC / COM / NO, on terminals 11–13, 21–23 and 31–33 respectively.
**Source.** `acs880_01_hardware_manual` PDF p186 (printed 186), *Control unit
— relay outputs*.

### G17 — "Where do I land the Modbus RTU pair on an ACS580-01 Type 4X?"
**Answer.** On the EIA-485 embedded fieldbus connection, shown under step 12,
*Connect the control cables*.
**Source.** `acs580_01_type4x_quickstart` PDF p8, *EIA-485 embedded fieldbus
connection*.

### G18 — "UL/NEC power connection diagram for shielded cable or conduit?"
**Answer.** The *UL (NEC) connection diagram with symmetrically shielded cable
or conduit*, given under step 11, *Connect the power cables*.
**Source.** `acs580_01_type4x_quickstart` PDF p4, *11. Connect the power
cables*.

### G19 — "Default I/O connections for the ABB standard macro on a Type 4X?"
**Answer.** The *Default I/O connections (ABB standard macro)* diagram, under
step 12, *Connect the control cables*.
**Source.** `acs580_01_type4x_quickstart` PDF p6.
**Why it is a good test.** The same content exists as G14/G15 in the hardware
manual. A retriever that ignores `product_family` and document kind can return
a defensible-looking but wrong citation — which citation accuracy should catch.

---

## prose (6)

### G20 — "Drive sat in storage two years. Anything before powering up?"
**Answer.** Yes. If the drive has not been powered up for a year or more you
must reform the DC link capacitors before energizing it. The guide refers to
*Related documents* or ABB technical support for the procedure.
**Source.** `acs580_01_type4x_quickstart` PDF p1, *2. Reform the capacitors*.

### G21 — "How long do I wait after switching off input power?"
**Answer.** 5 minutes, always, after disconnecting input power, to let the
intermediate circuit capacitors discharge — and only after isolating the drive
from all dangerous voltage sources and confirming it is safe to start work.
**Source.** `acs580_01_type4x_quickstart` PDF p1, *Safety instructions*.
**Why it matters here.** This is the kind of answer whose `safety_warning`
field must be copied verbatim under AS4.1, never paraphrased.

### G22 — "Can I run the motor cable in plastic conduit?"
**Answer.** Permitted in NEC installations, including underground and in wet
locations — but non-metallic conduit (Type LFNC) will not suppress EMC noise.
ABB recommends symmetrically shielded VFD motor cable; if conduit is used,
continuously conductive metallic conduit (Type EMT, RMC or LFMC) grounded at
both ends is preferred. Use a separate conduit run for each motor, and never
run input power wiring and motor wiring in the same conduit.
**Source.** `acs580_01_type4x_quickstart` PDF p1, *3. Select the cables and
fuses*.

### G23 — "Is it safe to work on the drive if the motor is still spinning?"
**Answer.** No — not with a permanent magnet motor. A rotating permanent
magnet motor energizes the drive, including its input and output terminals,
even with input power disconnected.
**Source.** `acs580_01_type4x_quickstart` PDF p1, *Safety instructions*.

### G24 — "Clearance under an ACS580 frame R6 when replacing an ACS550?" · scan target
**Answer.** Frames R6 and larger require 11.8 inches of free space below the
drive, measured from the fan — which sits higher than the ACS550's free-space
requirement. In a retrofit this can force longer cables or a lower mounting
point. Separately, the ACS580 has only five cable inlets, all under the drive,
where the ACS550 had inlets on the bottom and the sides.
**Source.** `acs550_to_acs580_replacement` PDF p16, *Low installation sites
and box installations*.

### G25 — "ACS580 calls it STO. What is it called on the ACS880?" ⟂ cross-manual
**Answer.** On the ACS880-01 it is the **XSTO** connector on the drive module
control unit. It only acts as a true Safe torque off input on an *inverter*
control unit. Both families carry the same warning: a short circuit in the
wiring between the switch and an STO terminal is a hazard.
**Source.** `acs880_01_hardware_manual` PDF p189 (printed 189), *Safe torque
off (XSTO)*; corroborated in `acs580_01_hardware_manual` PDF p450.
**Why it is a good test.** The only question in the set that cannot be
answered from a single document. It should be the clearest failure of the
naive baseline in M2.

---

## Related

`eval/out_of_corpus.jsonl` holds the 5 deliberately unanswerable questions that
AS3.2 needs for calibrating the refusal threshold. All 5 must refuse, and none
of the 25 above may refuse. OOC5 is the hard one — correct product family,
plausible phrasing, claim not in the corpus.
