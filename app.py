import streamlit as st
from openai import OpenAI
import pdfplumber
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
import numpy as np
import tempfile
import os
import json

client = OpenAI(api_key="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")
st.set_page_config(page_title="Haier HR Clone", layout="wide")

if "jobs" not in st.session_state:
    st.session_state.jobs = []
if "applicants" not in st.session_state:
    st.session_state.applicants = []

def generate_gpt4(prompt, temperature=0.7, max_tokens=600):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def plot_skill_radar(skill_scores):
    if not skill_scores:
        st.warning("No skills detected.")
        return
    labels = list(skill_scores.keys())
    stats = list(skill_scores.values())
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    stats.append(stats[0])
    angles.append(angles[0])
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, stats, 'o-', linewidth=2)
    ax.fill(angles, stats, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    st.pyplot(fig)

def extract_skills(text):
    prompt = (
        "From the following resume text, extract only the top relevant skills "
        "as a Python dictionary where keys are skill names and values are skill levels (1-10). "
        "Example format: {\"Boomi\": 9, \"Data Engineering\": 8, \"Python\": 7}.\n"
        f"Resume:\n{text}\n"
        "Return ONLY the Python dictionary."
    )
    result = generate_gpt4(prompt)
    try:
        skills = eval(result)
        if isinstance(skills, dict) and all(isinstance(v, (int, float)) for v in skills.values()):
            return skills
        else:
            raise ValueError("Not a valid dict of skill scores.")
    except:
        return {}

page = st.sidebar.selectbox("Navigation", ["Dashboard", "Create Job", "Applicants", "Interview", "Report"])

if page == "Dashboard":
    st.title("📊 Jobs at Hira.ai")
    if st.session_state.jobs:
        st.markdown("### All Published Jobs")
        st.table(st.session_state.jobs)
    else:
        st.info("No jobs created yet.")

elif page == "Create Job":
    st.title("📝 Create a New Job Posting")
    with st.form("job_form"):
        job_position = st.text_input("Job Position")
        job_location = st.text_input("Location")
        language = st.selectbox("Language", ["English", "French", "German"])
        skills = st.text_input("Major Skills (comma separated)")
        submitted = st.form_submit_button("Generate Job Description")
        if submitted:
            prompt = f"Write a job description for a {job_position} based in {job_location}, requiring skills: {skills}. Language: {language}"
            desc = generate_gpt4(prompt)
            st.session_state.jobs.append({
                "status": "Published",
                "position": job_position,
                "views": 0,
                "applicants": 0,
                "link": "/job/" + job_position.lower().replace(" ", "-")
            })
            st.text_area("Generated Job Description", desc, height=200)
            st.success("✅ Job added to dashboard")

elif page == "Applicants":
    st.title("👤 Applicant Management")
    uploaded = st.file_uploader("Upload Resume (PDF)", type="pdf")
    if uploaded:
        with pdfplumber.open(uploaded) as pdf:
            resume_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        skills = extract_skills(resume_text)
        if isinstance(skills, dict) and all(isinstance(v, (int, float)) for v in skills.values()):
            score = round(np.mean(list(skills.values())) * 10, 2)
        else:
            st.error("❌ Failed to extract valid skills. Please retry with a clearer resume.")
            score = 0.0
        name = uploaded.name.replace(".pdf", "")
        st.session_state.applicants.append({
            "name": name,
            "location": "Unknown",
            "score": f"{score}%",
            "status": "New Applicant",
            "skills": skills,
            "resume": resume_text
        })
        st.success(f"✅ {name} added with score {score}%")

    if st.session_state.applicants:
        st.table([{k: a[k] for k in ["name", "location", "score", "status"]} for a in st.session_state.applicants])
        selected = st.selectbox("Select Candidate", [a["name"] for a in st.session_state.applicants])
        for a in st.session_state.applicants:
            if a["name"] == selected:
                st.subheader(f"📄 Details for {a['name']}")
                st.write(f"**Score**: {a['score']}")
                plot_skill_radar(a['skills'])
                st.text_area("Resume Content", value=a['resume'], height=300)

elif page == "Interview":
    st.title("💬 AI Interview Simulation")
    candidates = [a["name"] for a in st.session_state.applicants]
    if candidates:
        selected = st.selectbox("Select Candidate", candidates)
        for a in st.session_state.applicants:
            if a["name"] == selected:
                prompt = f"Generate 3 smart interview questions for a candidate with this resume:\n{a['resume']}"
                questions = generate_gpt4(prompt).split("\n")
                for i, q in enumerate(questions):
                    st.markdown(f"**Q{i+1}:** {q}")
                    answer = st.text_area(f"{selected}'s Answer", key=f"answer_{i}")
                    if answer:
                        eval_prompt = (
                            f"Evaluate the following candidate answer in context of the interview question.\n"
                            f"Question: {q}\n"
                            f"Answer: {answer}\n\n"
                            "Rate the candidate on the following traits, from 1 to 10:\n"
                            "- Communication\n"
                            "- Confidence\n"
                            "- Relevance\n"
                            "- Leadership\n"
                            "- Technical Skills\n\n"
                            "Return the result as a Python dictionary, e.g.:\n"
                            "{\"Communication\": 8, \"Confidence\": 7, \"Relevance\": 9, \"Leadership\": 6, \"Technical Skills\": 8}"
                        )
                        try:
                            scores = eval(generate_gpt4(eval_prompt))
                            if "interview_scores" not in a:
                                a["interview_scores"] = []
                            a["interview_scores"].append(scores)
                            plot_skill_radar(scores)
                        except:
                            st.warning("Could not parse evaluation result.")

elif page == "Report":
    st.title("📋 Final AI Evaluation Report")
    if st.session_state.applicants:
        selected = st.selectbox("Select Candidate", [a["name"] for a in st.session_state.applicants])
        for a in st.session_state.applicants:
            if a["name"] == selected:
                if "interview_scores" in a and a["interview_scores"]:
                    avg_scores = {}
                    count = len(a["interview_scores"])
                    for score_set in a["interview_scores"]:
                        for k, v in score_set.items():
                            avg_scores[k] = avg_scores.get(k, 0) + v
                    for k in avg_scores:
                        avg_scores[k] = round(avg_scores[k] / count, 2)
                    plot_skill_radar(avg_scores)
                    st.write("### 🧠 Average Interview Scores")
                    st.json(avg_scores)
                else:
                    avg_scores = {}
                prompt = (
                    f"Write a hiring decision report for this candidate based on the following resume and average interview scores:\n"
                    f"Resume:\n{a['resume']}\n\n"
                    f"Skills: {a['skills']}\n\n"
                    f"Interview Scores: {avg_scores}"
                )
                report = generate_gpt4(prompt)
                st.text_area("Final Report", value=report, height=300)
                st.success("✅ Report ready")
