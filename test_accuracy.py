"""Minimal test - writes immediately to file at the start."""
import os, sys, traceback

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_results.txt")

try:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("STARTED\n")
        f.flush()
        
        # Test 1: import pipeline module-level vars
        try:
            import re
            # Test the functions directly without importing the module
            # to avoid triggering NLTK download
            
            def count_alpha(word):
                return sum(1 for c in word if c.isalpha())
            
            def is_url_like(word):
                w = word.lower()
                if re.search(r'\.(com|org|net|io|dev|ai|edu|gov|co)\b', w):
                    return True
                return False
            
            def is_hard_signal(word):
                if not word or " " in word:
                    return False
                if is_url_like(word):
                    return False
                if count_alpha(word) < 2:
                    return False
                if any(c.isdigit() for c in word) and count_alpha(word) >= 2:
                    return True
                if any(c in ("+", "#", "/") for c in word) and count_alpha(word) >= 1:
                    return True
                if "." in word and count_alpha(word) >= 3 and not re.match(r'^[a-z]\.[a-z]\.$', word.lower()):
                    return True
                if re.match(r"^[A-Z]{2,8}$", word):
                    return True
                if any(c.isupper() for c in word) and any(c.islower() for c in word):
                    return True
                return False
            
            def is_noise(phrase):
                p = phrase.strip()
                if not p:
                    return True
                if re.match(r'^[\d\s%.,]+$', p):
                    return True
                if is_url_like(p):
                    return True
                if re.match(r'^\d{1,4}$', p.strip()):
                    return True
                words = p.split()
                if len(words) >= 2:
                    num_count = sum(1 for w in words if re.match(r'^\d+[%]?$', w))
                    if num_count / len(words) > 0.5:
                        return True
                clean = re.sub(r'[^a-zA-Z]', '', p)
                if len(clean) < 2:
                    return True
                return False
            
            f.write("\n=== HARD SIGNAL TESTS ===\n")
            tests = [
                ("123", False), ("33", False), ("21", False), ("7", False),
                ("github.com", False), ("e.g.", False),
                ("OAuth2", True), ("ES6", True), ("GPT4", True),
                ("C++", True), ("C#", True), ("CI/CD", True),
                ("Node.js", True), ("ASP.NET", True),
                ("REST", True), ("HTML", True), ("API", True), ("SQL", True),
                ("JavaScript", True), ("TypeScript", True),
            ]
            pass_count = 0
            for tok, want in tests:
                got = is_hard_signal(tok)
                ok = got == want
                if ok: pass_count += 1
                f.write(f"  {'PASS' if ok else 'FAIL'}: is_hard_signal('{tok}') = {got} (want {want})\n")
            f.write(f"\nPassed: {pass_count}/{len(tests)}\n")
            
            f.write("\n=== NOISE FILTER TESTS ===\n")
            noise_tests = [
                ("123", True), ("33 %", True), ("21", True),
                ("7 product specialists", True), ("github.com", True), ("e.g.", True),
                ("power bi", False), ("machine learning", False),
                ("a/b testing", False), ("OAuth2", False),
            ]
            pass_count2 = 0
            for phrase, want in noise_tests:
                got = is_noise(phrase)
                ok = got == want
                if ok: pass_count2 += 1
                f.write(f"  {'PASS' if ok else 'FAIL'}: is_noise('{phrase}') = {got} (want {want})\n")
            f.write(f"\nPassed: {pass_count2}/{len(noise_tests)}\n")
            
            f.write("\n=== MODULE IMPORT TEST ===\n")
            from pipeline import _is_hard_signal as hs, _is_noise_candidate as nc, _GENERIC_SINGLE_NOUNS, _TRIM_START
            f.write(f"  pipeline import: OK\n")
            f.write(f"  _is_hard_signal('123') = {hs('123')}\n")
            f.write(f"  _is_hard_signal('OAuth2') = {hs('OAuth2')}\n")
            f.write(f"  _is_noise_candidate('33 %') = {nc('33 %')}\n")
            f.write(f"  'job' in _GENERIC_SINGLE_NOUNS = {'job' in _GENERIC_SINGLE_NOUNS}\n")
            f.write(f"  'leveraged' in _TRIM_START = {'leveraged' in _TRIM_START}\n")
            f.write(f"  'conducted' in _TRIM_START = {'conducted' in _TRIM_START}\n")
            
        except Exception as e:
            f.write(f"ERROR: {e}\n")
            traceback.print_exc(file=f)
        
        f.write("\nDONE\n")
        f.flush()

except Exception as e:
    with open(OUT, "w") as f:
        f.write(f"FATAL: {e}\n")
        traceback.print_exc(file=f)
