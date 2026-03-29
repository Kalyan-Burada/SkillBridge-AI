import sys
from pipeline import _get_nlp, _get_model
from implication_engine import ImplicationEngine

with open('impl_results.txt', 'w', encoding='utf-8') as f:
    f.write("Initializing...\n")
    _get_nlp()
    _get_model()

    jd_skills = ["tensorflow", "aws", "pandas", "scikit-learn", "agile"]
    resume_skills = ["artificial intelligence", "machine learning models", "power power bi bi", "precise cta", "patient needs", "scrum master"]

    f.write("TESTING IMPLICATION ENGINE\n")
    f.write(f"JD skills: {jd_skills}\n")
    f.write(f"Resume skills: {resume_skills}\n")
    f.write("-" * 50 + "\n")

    engine = ImplicationEngine()

    for jd in jd_skills:
        is_implied, best_match, pass_label = engine.check_implied(jd, resume_skills)
        if is_implied:
            f.write(f"✓ {jd} is implied by {best_match} (Pass: {pass_label})\n")
        else:
            f.write(f"✗ {jd} is missing\n")
    
    f.write("Finished.\n")
