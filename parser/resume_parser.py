import re


def parse_resume(text):

    data = {}

    # ==========================================
    # 1. NAME
    # ==========================================

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if lines:
        # Usually the candidate's name is near the top
        name = lines[0]

        # Avoid treating common headings as name
        unwanted = [
            "resume",
            "curriculum vitae",
            "cv",
            "profile",
            "contact"
        ]

        if name.lower() not in unwanted:
            data["name"] = name
        else:
            data["name"] = "Not Found"
    else:
        data["name"] = "Not Found"


    # ==========================================
    # 2. EMAIL
    # ==========================================

    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'

    email = re.search(email_pattern, text)

    if email:
        data["email"] = email.group()
    else:
        data["email"] = "Not Found"


    # ==========================================
    # 3. PHONE NUMBER
    # ==========================================

    phone_pattern = r'(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}'

    phone = re.search(phone_pattern, text)

    if phone:
        data["phone"] = phone.group()
    else:
        data["phone"] = "Not Found"


    # ==========================================
    # 4. SKILLS
    # ==========================================

    possible_skills = [
        "Python",
        "Java",
        "C",
        "C++",
        "C#",
        "SQL",
        "HTML",
        "CSS",
        "JavaScript",
        "React",
        "Node.js",
        "Machine Learning",
        "Deep Learning",
        "Data Science",
        "Artificial Intelligence",
        "NLP",
        "Django",
        "Flask",
        "Git",
        "GitHub",
        "MySQL",
        "MongoDB",
        "Oracle",
        "AWS",
        "Docker",
        "Power BI",
        "Excel"
    ]

    found_skills = []

    for skill in possible_skills:

        if skill.lower() in text.lower():
            found_skills.append(skill)

    data["skills"] = found_skills


    # ==========================================
    # 5. EDUCATION
    # ==========================================

    education_keywords = [
        "B.Tech",
        "B.E",
        "Bachelor of Technology",
        "Bachelor of Engineering",
        "B.Sc",
        "BCA",
        "M.Tech",
        "M.E",
        "Master of Technology",
        "M.Sc",
        "MCA",
        "MBA",
        "Diploma",
        "Higher Secondary",
        "12th",
        "10th",
        "Secondary"
    ]

    found_education = []

    for education in education_keywords:

        if education.lower() in text.lower():
            found_education.append(education)

    data["education"] = found_education


    # ==========================================
    # 6. EXPERIENCE - SECTION-WISE EXTRACTION
    # ==========================================

    section_pattern = re.compile(
        r"^\s*(experience|work experience|professional experience|"
        r"employment history|employment|projects?|education|"
        r"certifications?|internships?|skills|technical skills|"
        r"summary|profile|languages|references)\b\s*[:\-–]?\s*(.*)$",
        re.IGNORECASE
    )

    section_headings = {
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "employment",
        "projects",
        "project",
        "education",
        "certification",
        "certifications",
        "internship",
        "internships",
        "skills",
        "technical skills",
        "summary",
        "profile",
        "languages",
        "references"
    }

    current_section = None
    experience_lines = []

    for line in lines:
        match = section_pattern.match(line)

        if match:
            heading = re.sub(r"\s+", " ", match.group(1)).strip().lower()
            remaining_text = match.group(2).strip()

            if heading in section_headings:
                current_section = heading

                # Capture text appearing after the heading
                # on the same line, if any.
                if heading in {
                    "experience",
                    "work experience",
                    "professional experience",
                    "employment history",
                    "employment"
                }:
                    if remaining_text:
                        experience_lines.append(remaining_text)

                continue

        # Collect only content inside the Experience section.
        if current_section in {
            "experience",
            "work experience",
            "professional experience",
            "employment history",
            "employment"
        }:
            experience_lines.append(line.strip())

    experience_text = "\n".join(
        line for line in experience_lines if line
    ).strip()

    data["experience"] = experience_text or "Not Found"


    return data