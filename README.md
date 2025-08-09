# Smart-Timetable

A simple and interactive web app built with **Streamlit** that generates weekly college timetables based on user inputs for courses, branches, sections, theory subjects, electives, and labs. The app ensures no overlapping elective periods across sections and outputs a well-structured Excel timetable.

---

## Features

- Input course details: Course name, branch, semester, sections.
- Add theory subjects with required weekly periods.
- Define elective groups with multiple options and required periods.
- Add lab classes and schedule lab periods intelligently.
- Assign home classrooms per section and extra classrooms for electives.
- Ensures no two elective classes overlap across sections.
- Generates a color-coded Excel file with timetables for all sections.
- Simple UI using Streamlit with download option for the generated timetable.

---

## Getting Started

### Prerequisites

- Python 3.7 or higher
- `streamlit`
- `pandas`
- `xlsxwriter`

Install dependencies:

```bash
pip install streamlit pandas xlsxwriterash
