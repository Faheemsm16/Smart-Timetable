import streamlit as st
import random
import pandas as pd
from collections import defaultdict
import io

random.seed(42)

# Constants
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
PERIODS_PER_DAY = 7
PRAYER_DAY = "Fri"
PRAYER_PERIOD_INDEX = 4

def make_empty_grid():
    return [["" for _ in range(PERIODS_PER_DAY)] for _ in DAYS]

def slot_candidates():
    pre = [(d,p) for d in range(len(DAYS)) for p in range(0,4)]
    post = [(d,p) for d in range(len(DAYS)) for p in range(4, PERIODS_PER_DAY)]
    pre = [s for s in pre if not (DAYS[s[0]]==PRAYER_DAY and s[1]==PRAYER_PERIOD_INDEX)]
    post = [s for s in post if not (DAYS[s[0]]==PRAYER_DAY and s[1]==PRAYER_PERIOD_INDEX)]
    random.shuffle(pre)
    random.shuffle(post)
    return pre + post

def staff_id(sub):
    return f"STAFF::{sub}"

def generate_timetable(inputs):
    course = inputs['course']
    branch = inputs['branch']
    semester = inputs['semester']
    sections = inputs['sections']
    theory_subjects = inputs['theory_subjects']
    theory_periods_req = inputs['theory_periods_req']
    electives = inputs['electives']
    labs = inputs['labs']
    lab_periods_req = inputs['lab_periods_req']
    home_rooms = inputs['home_rooms']
    extra_rooms = inputs['extra_rooms']

    timetables = {sec: make_empty_grid() for sec in sections}
    staff_busy = defaultdict(set)
    assigned_today = defaultdict(set)
    SLOT_CANDIDATES = slot_candidates()

    def slot_allowed(sec, d, p, subj, prevent_same_day=True, require_free=True):
        if DAYS[d] == PRAYER_DAY and p == PRAYER_PERIOD_INDEX:
            return False
        if require_free and timetables[sec][d][p] != "":
            return False
        if prevent_same_day and subj in assigned_today[(sec, d)]:
            return False
        if staff_id(subj) in staff_busy[(d,p)]:
            return False
        return True

    def assign_slot_single(subj, sec, prefer_pre_lunch=True, allow_afternoon=True):
        candidates = SLOT_CANDIDATES.copy()
        for (d,p) in candidates:
            if p >= 4 and not allow_afternoon:
                continue
            if slot_allowed(sec, d, p, subj, prevent_same_day=True):
                timetables[sec][d][p] = f"{subj} ({home_rooms[sections.index(sec)]})"
                staff_busy[(d,p)].add(staff_id(subj))
                assigned_today[(sec,d)].add(subj)
                return True
        for (d,p) in candidates:
            if p >= 4 and not allow_afternoon:
                continue
            if slot_allowed(sec, d, p, subj, prevent_same_day=False):
                timetables[sec][d][p] = f"{subj} ({home_rooms[sections.index(sec)]})"
                staff_busy[(d,p)].add(staff_id(subj))
                assigned_today[(sec,d)].add(subj)
                return True
        return False

    # Place labs
    for sec in sections:
        afternoon_start_candidates = []
        for d in range(len(DAYS)):
            for p in range(PERIODS_PER_DAY - 1):
                if (DAYS[d] == PRAYER_DAY and (p == PRAYER_PERIOD_INDEX or p+1 == PRAYER_PERIOD_INDEX)):
                    continue
                afternoon_start_candidates.append((d,p))
        random.shuffle(afternoon_start_candidates)
        afternoon_start_candidates.sort(key=lambda s: (0 if s[1] >= 4 else 1, random.random()))

        for lab in labs:
            periods_needed = lab_periods_req[lab]
            blocks_needed = periods_needed // 2
            remainder = periods_needed % 2
            placed_blocks = 0
            placed_singles = 0
            tries = 0
            while placed_blocks < blocks_needed and tries < 1000:
                for (d,p) in afternoon_start_candidates:
                    if p+1 >= PERIODS_PER_DAY:
                        continue
                    if timetables[sec][d][p] != "" or timetables[sec][d][p+1] != "":
                        continue
                    if staff_id(lab) in staff_busy[(d,p)] or staff_id(lab) in staff_busy[(d,p+1)]:
                        continue
                    timetables[sec][d][p] = f"{lab} (Lab)"
                    timetables[sec][d][p+1] = f"{lab} (Lab)"
                    staff_busy[(d,p)].add(staff_id(lab))
                    staff_busy[(d,p+1)].add(staff_id(lab))
                    assigned_today[(sec,d)].add(lab)
                    placed_blocks += 1
                    break
                tries += 1
            tries = 0
            while remainder == 1 and placed_singles < 1 and tries < 500:
                cand_slots = [(d,p) for d in range(len(DAYS)) for p in range(PERIODS_PER_DAY) if timetables[sec][d][p]=="" and not (DAYS[d]==PRAYER_DAY and p==PRAYER_PERIOD_INDEX)]
                random.shuffle(cand_slots)
                found = False
                for (d,p) in cand_slots:
                    if staff_id(lab) in staff_busy[(d,p)]:
                        continue
                    timetables[sec][d][p] = f"{lab} (Lab)"
                    staff_busy[(d,p)].add(staff_id(lab))
                    assigned_today[(sec,d)].add(lab)
                    placed_singles += 1
                    found = True
                    break
                if found:
                    break
                tries += 1

    # Assign theory subjects
    for subj in theory_subjects:
        req = theory_periods_req[subj]
        for sec in sections:
            assigned = 0
            attempts = 0
            while assigned < req and attempts < 1000:
                if assign_slot_single(subj, sec):
                    assigned += 1
                attempts += 1

    # Assign electives ensuring no overlap globally
    elective_busy_slots = set()
    for egrp in electives:
        opts = egrp['options']
        periods_needed = egrp['periods']
        for sec in sections:
            assigned = 0
            tries = 0
            while assigned < periods_needed and tries < 2000:
                candidates = slot_candidates()
                placed = False
                for (d,p) in candidates:
                    if timetables[sec][d][p] != "":
                        continue
                    if any(staff_id(opt) in staff_busy[(d,p)] for opt in opts):
                        continue
                    if any(opt in assigned_today[(sec,d)] for opt in opts):
                        continue
                    if (d,p) in elective_busy_slots:
                        continue
                    labels = []
                    home_room = home_rooms[sections.index(sec)]
                    for i_opt, opt_name in enumerate(opts):
                        if i_opt == 0:
                            room = home_room
                        else:
                            room = extra_rooms[(i_opt-1) % len(extra_rooms)] if extra_rooms else f"ExtraRoom_{i_opt}"
                        labels.append(f"{opt_name} ({room})")
                    cell_text = " / ".join(labels)
                    timetables[sec][d][p] = cell_text
                    for opt_name in opts:
                        staff_busy[(d,p)].add(staff_id(opt_name))
                        assigned_today[(sec,d)].add(opt_name)
                    elective_busy_slots.add((d,p))
                    placed = True
                    assigned += 1
                    break
                if not placed:
                    tries += 1
                else:
                    tries = 0

    # Fill empty slots with Free
    for sec in sections:
        for d in range(len(DAYS)):
            for p in range(PERIODS_PER_DAY):
                if DAYS[d] == PRAYER_DAY and p == PRAYER_PERIOD_INDEX:
                    continue
                if timetables[sec][d][p] == "":
                    timetables[sec][d][p] = "Free"

    # Mark Prayer Time
    for sec in sections:
        d_idx = DAYS.index(PRAYER_DAY)
        timetables[sec][d_idx][PRAYER_PERIOD_INDEX] = "Prayer Time"

    dfs = {}
    for sec in sections:
        df = pd.DataFrame(timetables[sec], index=DAYS, columns=[f"P{p+1}" for p in range(PERIODS_PER_DAY)])
        dfs[sec] = df
    return dfs

# Streamlit UI

st.title("College Timetable Generator")

course = st.text_input("Course (e.g., B.Tech)")
branch = st.text_input("Branch (e.g., CSE)")
semester = st.text_input("Semester (e.g., III)")

sections_str = st.text_input("Sections (comma separated, e.g., A,B,C,D)")
sections = [s.strip() for s in sections_str.split(",") if s.strip()]

num_theory = st.number_input("Number of theory subjects", min_value=0, step=1, value=0)

theory_subjects = []
theory_periods_req = {}

if num_theory > 0:
    st.write("Enter theory subject details:")
    for i in range(num_theory):
        subj = st.text_input(f"Theory subject {i+1} name", key=f"theory_name_{i}")
        p = st.number_input(f"Periods per week for {subj}", min_value=0, step=1, key=f"theory_period_{i}")
        theory_subjects.append(subj)
        theory_periods_req[subj] = p

num_electives = st.number_input("Number of elective groups", min_value=0, step=1, value=0)

electives = []
if num_electives > 0:
    st.write("Enter elective group details:")
    for e in range(num_electives):
        opts_count = st.number_input(f"Number of options for elective group {e+1}", min_value=1, step=1, value=1, key=f"elective_opts_{e}")
        opts = []
        for o in range(opts_count):
            opt_name = st.text_input(f"Elective group {e+1} Option {o+1} name", key=f"elective_{e}_opt_{o}")
            opts.append(opt_name)
        p = st.number_input(f"Periods per week for elective group {e+1}", min_value=0, step=1, key=f"elective_periods_{e}")
        electives.append({'options': opts, 'periods': p})

num_labs = st.number_input("Number of labs", min_value=0, step=1, value=0)

labs = []
lab_periods_req = {}

if num_labs > 0:
    st.write("Enter lab details:")
    for i in range(num_labs):
        lab_name = st.text_input(f"Lab class {i+1} name", key=f"lab_name_{i}")
        lab_period = st.number_input(f"Periods per week for {lab_name}", min_value=0, step=1, key=f"lab_period_{i}")
        labs.append(lab_name)
        lab_periods_req[lab_name] = lab_period

st.write("Enter home classroom names for each section:")
home_rooms = []
if sections:
    for sec in sections:
        room = st.text_input(f"Home classroom for section {sec}", key=f"home_room_{sec}")
        home_rooms.append(room)

max_opts = max((len(e['options']) for e in electives), default=0)
extra_needed = max(0, max_opts - 1)

extra_rooms = []
if extra_needed > 0:
    st.write(f"Electives have up to {max_opts} options. Please enter {extra_needed} extra classroom names for option rooms:")
    for i in range(extra_needed):
        room = st.text_input(f"Extra classroom name {i+1}", key=f"extra_room_{i}")
        extra_rooms.append(room)

if st.button("Generate Timetable"):
    if not course or not branch or not semester or not sections:
        st.error("Please fill in all course, branch, semester and sections.")
    elif len(home_rooms) < len(sections) or any(r.strip()=="" for r in home_rooms):
        st.error("Please enter all home classroom names for each section.")
    elif extra_needed > 0 and (len(extra_rooms) < extra_needed or any(r.strip()=="" for r in extra_rooms)):
        st.error("Please enter all extra classroom names for elective option rooms.")
    else:
        inputs = {
            'course': course,
            'branch': branch,
            'semester': semester,
            'sections': sections,
            'theory_subjects': theory_subjects,
            'theory_periods_req': theory_periods_req,
            'electives': electives,
            'labs': labs,
            'lab_periods_req': lab_periods_req,
            'home_rooms': home_rooms,
            'extra_rooms': extra_rooms,
        }
        dfs = generate_timetable(inputs)
        st.success("Timetable generated successfully!")

        for sec, df in dfs.items():
            st.write(f"### Timetable for Section {sec}")
            st.dataframe(df)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for sec, df in dfs.items():
                sheetname = f"{course}-{branch}-{sec}-Sem{semester}"
                df.to_excel(writer, sheet_name=sheetname)
        output.seek(0)

        st.download_button(
            label="Download Timetable Excel",
            data=output,
            file_name="College_Timetable.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
