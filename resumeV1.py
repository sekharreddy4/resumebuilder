import os
import streamlit as st
from langchain_groq import ChatGroq
from langchain.schema.messages import AIMessage
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import json
import re

# Load environment variables
load_dotenv()
groqapikey = os.getenv("api-key")

if not groqapikey:
    st.error("Error: GROQ_API_KEY not found in .env file.")
    st.stop()

# Initialize the LLM with Groq
llm = ChatGroq(
    temperature=0.1,
    model_name="llama-3.1-8b-instant",
    api_key=groqapikey
)


def create_pdf(content):
    """Create PDF from generated resume text"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    flowables = []

    # Custom styles
    header_style = styles["Heading1"]
    header_style.textColor = "#2B547E"
    section_style = styles["Heading2"]
    section_style.textColor = "#2B547E"

    # Add header
    flowables.append(Paragraph(content.get("name", ""), header_style))
    flowables.append(Spacer(1, 12))

    # Add contact info
    contact_info = f"{content.get('email', '')} | {content.get('phone', '')} | {content.get('location', '')}"
    flowables.append(Paragraph(contact_info, styles["Normal"]))
    flowables.append(Spacer(1, 24))

    # Add sections
    sections = ['summary', 'experience', 'education', 'skills', 'certifications']
    for section in sections:
        if content.get(section):
            flowables.append(Paragraph(section.capitalize(), section_style))
            flowables.append(Spacer(1, 12))
            if isinstance(content[section], list):
                for item in content[section]:
                    flowables.append(Paragraph(f"• {item}", styles["Normal"]))
            else:
                flowables.append(Paragraph(content[section], styles["Normal"]))
            flowables.append(Spacer(1, 24))

    doc.build(flowables)
    return buffer.getvalue()


def generate_resume(user_data):
    """Generate resume content using LLM"""
    prompt = f"""
    Create a professional resume based on the following information:

    {json.dumps(user_data, indent=2)}

    Requirements:
      - Use professional language.
      - Include all provided details.
      - Format the response as valid JSON with these fields:
        name, email, phone, location, summary, experience (list), education (list), skills (list), certifications (list).
      - Do not include any additional text outside the JSON structure.
      - Ensure proper escaping of special characters.
      - Structure the JSON properly.
    """

    try:
        response = llm.invoke([AIMessage(content=prompt)])
        raw_response = response.content

        # Extract JSON from the response
        json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        else:
            st.error(f"No valid JSON found in the response:\n{raw_response}")
            return None

    except json.JSONDecodeError as e:
        st.error(f"JSON Parsing Failed. Raw LLM Response:\n{raw_response}")
        return None
    except Exception as e:
        st.error(f"Error generating resume: {str(e)}")
        return None


# Streamlit UI
st.title("AI Resume Builder")
st.markdown("📄 Get a professional resume in 2 minutes")

# User Input Form
with st.form("user_input"):
    st.subheader("Your Information")
    name = st.text_input("Full Name*")
    email = st.text_input("Email*")
    phone = st.text_input("Phone Number")
    location = st.text_input("Location")

    st.subheader("Professional Details")
    summary = st.text_area("Career Summary (2-3 sentences)")
    experience = st.text_area("Work Experience (One per line)*",
                              help="Example:\nSoftware Engineer @ Google (2020-Present)\n- Developed...")
    education = st.text_area("Education (One per line)",
                             help="Example:\nBS Computer Science @ MIT (2016-2020)")
    skills = st.text_area("Technical Skills (Comma separated)*",
                          help="Example:\nPython, Machine Learning, SQL")
    certifications = st.text_area("Certifications (One per line)")

    submitted = st.form_submit_button("Generate Resume")

# Process Input
if submitted:
    if not name or not email or not experience or not skills:
        st.error("Please fill required fields (*)")
        st.stop()

    user_data = {
        "name": name,
        "email": email,
        "phone": phone,
        "location": location,
        "summary": summary,
        "experience": [exp.strip() for exp in experience.split('\n') if exp.strip()],
        "education": [edu.strip() for edu in education.split('\n') if edu.strip()],
        "skills": [skill.strip() for skill in skills.split(',') if skill.strip()],
        "certifications": [cert.strip() for cert in certifications.split('\n') if cert.strip()]
    }

    with st.spinner("Crafting your professional resume..."):
        resume_content = generate_resume(user_data)

    if resume_content:
        # Display preview
        st.subheader("Resume Preview")
        st.write("### " + resume_content.get("name", ""))
        st.write(f"**Email:** {resume_content.get('email', '')} | **Phone:** {resume_content.get('phone', '')}")
        st.write(f"**Location:** {resume_content.get('location', '')}")

        for section in ['summary', 'experience', 'education', 'skills', 'certifications']:
            if resume_content.get(section):
                st.write(f"#### {section.capitalize()}")
                if isinstance(resume_content[section], list):
                    for item in resume_content[section]:
                        st.write(f"- {item}")
                else:
                    st.write(resume_content[section])

        # Generate PDF
        pdf_bytes = create_pdf(resume_content)
        st.success("✅ Resume generated successfully!")

        # Download button
        st.download_button(
            label="📥 Download PDF Resume",
            data=pdf_bytes,
            file_name=f"{name.replace(' ', '_')}_Resume.pdf",
            mime="application/pdf"
        )
    else:
        st.error("Failed to generate resume. Please try again or contact support.")
