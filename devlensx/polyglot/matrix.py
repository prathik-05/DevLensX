import json, pathlib, sys
from devlensx.polyglot.validator import PolyglotValidator
from devlensx.polyglot.models import LanguageStatus

MATRIX_PATH = pathlib.Path("POLYGLOT_VALIDATION_MATRIX.json")

def generate_matrix():
    results = PolyglotValidator.validate_all()
    data = {lang: rec.to_dict() for lang, rec in results.items()}
    # Print matrix (ascii-safe on Windows)
    try:
        import sys
        sys.stdout.reconfigure(encoding="utf-8")
    except: pass
    print("Polyglot Validation Matrix")
    print("="*40)
    for lang, rec in results.items():
        status = rec.status.value
        icon = "[OK]" if rec.status == LanguageStatus.VALIDATED else "[PENDING]" if rec.status == LanguageStatus.VALIDATION_PENDING else "[FAIL]" if rec.status == LanguageStatus.VALIDATION_FAILED else "[ ]"
        try:
            print(f"{lang:12} {icon} {status}")
            if rec.status == LanguageStatus.VALIDATED:
                print(f"  repo={rec.real_repository} files={rec.files_parsed} symbols={rec.symbols} rel={rec.relationships}")
            if rec.failure_stage:
                print(f"  failure: {rec.failure_stage}")
        except UnicodeEncodeError:
            print(f"{lang:12} {status}")
    MATRIX_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"\nSaved to {MATRIX_PATH}")
    return data

def load_matrix():
    if MATRIX_PATH.exists():
        return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    return {}

if __name__ == "__main__":
    generate_matrix()
