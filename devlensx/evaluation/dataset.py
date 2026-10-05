import json
from pathlib import Path
from typing import List, Dict, Any
from devlensx.evaluation.models import GoldenCase

DATASET_PATH = Path("GOLDEN_EVALUATION_DATASET.json")
DATASET_DIR = Path("tests/golden/dataset")

def load_dataset() -> List[GoldenCase]:
    cases = []
    if DATASET_PATH.exists():
        data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        for c in data.get("cases", []):
            cases.append(GoldenCase.from_dict(c))
        return cases
    # Fallback: load from dataset dir
    for p in DATASET_DIR.glob("*.json"):
        data = json.loads(p.read_text(encoding="utf-8"))
        for c in data.get("cases", data if isinstance(data, list) else []):
            if isinstance(c, dict) and "id" in c:
                cases.append(GoldenCase.from_dict(c))
    return cases

def save_dataset(cases: List[GoldenCase], version: str = "1.0"):
    data = {"dataset_version": version, "cases": [c.to_dict() for c in cases]}
    DATASET_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return DATASET_PATH

def generate_default_dataset() -> List[GoldenCase]:
    from devlensx.evaluation.models import Verdict, ExpectedClaim, ExpectedEvidence
    cases = [
        # PetClinic 12
        GoldenCase(id="petclinic_owner_location", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="Where is OwnerController defined?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("OwnerController","DEFINED_IN","OwnerController.java"), expected_evidence=ExpectedEvidence(file="OwnerController.java", symbol="OwnerController"), description="OwnerController location"),
        GoldenCase(id="petclinic_repo_location", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="Where is OwnerRepository defined?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("OwnerRepository","DEFINED_IN","OwnerRepository.java"), expected_evidence=ExpectedEvidence(file="OwnerRepository.java", symbol="OwnerRepository")),
        GoldenCase(id="petclinic_controller_depends_repo", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="Does OwnerController depend on OwnerRepository?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("OwnerController","DEPENDS_ON","OwnerRepository"), expected_evidence=ExpectedEvidence(file="OwnerController.java", symbol="OwnerController")),
        GoldenCase(id="petclinic_controller_depends_service", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="Does OwnerController depend on OwnerService?", mode="CODEMAP", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("OwnerController","DEPENDS_ON","OwnerService"), expected_evidence=ExpectedEvidence(file="OwnerController.java", symbol="OwnerController")),
        GoldenCase(id="petclinic_owner_flow", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="How does the owner request reach persistence?", mode="CODEMAP", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("OwnerController","CALLS","OwnerService"), expected_evidence=ExpectedEvidence(file="OwnerController.java", symbol="OwnerController")),
        GoldenCase(id="petclinic_persistence", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="What classes implement the persistence layer?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("OwnerRepository","IMPLEMENTS","Repository"), expected_evidence=ExpectedEvidence(file="OwnerRepository.java", symbol="OwnerRepository")),
        GoldenCase(id="petclinic_architecture", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="What are the major architectural layers?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("OwnerController","LAYER","Controller"), expected_evidence=ExpectedEvidence(file="OwnerController.java", symbol="OwnerController")),
        GoldenCase(id="petclinic_docs", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="Explain OwnerController", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("OwnerController","DEFINED_IN","OwnerController.java"), expected_evidence=ExpectedEvidence(file="OwnerController.java", symbol="OwnerController")),
        GoldenCase(id="petclinic_redis_negative", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="Does this application use Redis?", mode="FAST", expected_verdict=Verdict.INSUFFICIENT_EVIDENCE, expected_claim=ExpectedClaim("Application","USES","Redis"), expected_evidence=ExpectedEvidence(file="", symbol="")),
        GoldenCase(id="petclinic_kafka_negative", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="Does this application use Kafka?", mode="FAST", expected_verdict=Verdict.INSUFFICIENT_EVIDENCE, expected_claim=ExpectedClaim("Application","USES","Kafka"), expected_evidence=ExpectedEvidence(file="", symbol="")),
        GoldenCase(id="petclinic_mongo_negative", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="Does this application use MongoDB?", mode="FAST", expected_verdict=Verdict.INSUFFICIENT_EVIDENCE, expected_claim=ExpectedClaim("Application","USES","MongoDB"), expected_evidence=ExpectedEvidence(file="", symbol="")),
        GoldenCase(id="petclinic_snapshot_isolation", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="Does PetClinic contain AIPlayer?", mode="FAST", expected_verdict=Verdict.INSUFFICIENT_EVIDENCE, expected_claim=ExpectedClaim("AIPlayer","DEFINED_IN","AIPlayer.java"), expected_evidence=ExpectedEvidence(file="", symbol="")),
        # sp-portfolio 8
        GoldenCase(id="portfolio_spdevprovider", repository="sp-portfolio", repository_path="eval_repos/sp-portfolio", question="Where is SPDevProvider defined?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("SPDevProvider","DEFINED_IN","SPDevProvider.tsx"), expected_evidence=ExpectedEvidence(file="SPDevProvider", symbol="SPDevProvider")),
        GoldenCase(id="portfolio_theme", repository="sp-portfolio", repository_path="eval_repos/sp-portfolio", question="Where is the theme configuration defined?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("Theme","DEFINED_IN","theme.ts"), expected_evidence=ExpectedEvidence(file="theme", symbol="Theme")),
        GoldenCase(id="portfolio_component_rel", repository="sp-portfolio", repository_path="eval_repos/sp-portfolio", question="What components use the application context?", mode="CODEMAP", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("Component","USES","Context"), expected_evidence=ExpectedEvidence(file="SPDevProvider", symbol="SPDevProvider")),
        GoldenCase(id="portfolio_state", repository="sp-portfolio", repository_path="eval_repos/sp-portfolio", question="How is state management implemented?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("SPDevProvider","PROVIDES","Context"), expected_evidence=ExpectedEvidence(file="SPDevProvider", symbol="SPDevProvider")),
        GoldenCase(id="portfolio_effect", repository="sp-portfolio", repository_path="eval_repos/sp-portfolio", question="What visual effects are implemented?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("Effect","DEFINED_IN","effects"), expected_evidence=ExpectedEvidence(file="effects", symbol="Effect")),
        GoldenCase(id="portfolio_structure", repository="sp-portfolio", repository_path="eval_repos/sp-portfolio", question="What is the project structure?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("Project","HAS_STRUCTURE","src"), expected_evidence=ExpectedEvidence(file="src", symbol="Project")),
        GoldenCase(id="portfolio_redis_negative", repository="sp-portfolio", repository_path="eval_repos/sp-portfolio", question="Does this application use Redis?", mode="FAST", expected_verdict=Verdict.INSUFFICIENT_EVIDENCE, expected_claim=ExpectedClaim("Application","USES","Redis"), expected_evidence=ExpectedEvidence(file="", symbol="")),
        GoldenCase(id="portfolio_spring_negative", repository="sp-portfolio", repository_path="eval_repos/sp-portfolio", question="Does this repository use Spring or JPA?", mode="FAST", expected_verdict=Verdict.INSUFFICIENT_EVIDENCE, expected_claim=ExpectedClaim("Application","USES","Spring"), expected_evidence=ExpectedEvidence(file="", symbol="")),
        # battleship 8
        GoldenCase(id="battleship_aiplayer", repository="battleship-python", repository_path="eval_repos/battleship-python", question="Where is the AI player defined?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("AIPlayer","DEFINED_IN","ai_player.py"), expected_evidence=ExpectedEvidence(file="ai_player.py", symbol="AIPlayer")),
        GoldenCase(id="battleship_gamelogic", repository="battleship-python", repository_path="eval_repos/battleship-python", question="Where is the main game logic defined?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("Game","DEFINED_IN","game.py"), expected_evidence=ExpectedEvidence(file="game.py", symbol="Game")),
        GoldenCase(id="battleship_module_rel", repository="battleship-python", repository_path="eval_repos/battleship-python", question="How does the game flow between modules?", mode="CODEMAP", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("Game","CALLS","Player"), expected_evidence=ExpectedEvidence(file="game.py", symbol="Game")),
        GoldenCase(id="battleship_entry", repository="battleship-python", repository_path="eval_repos/battleship-python", question="Where is the entry point?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("Game","DEFINED_IN","game.py"), expected_evidence=ExpectedEvidence(file="game.py", symbol="Game")),
        GoldenCase(id="battleship_arch", repository="battleship-python", repository_path="eval_repos/battleship-python", question="What is the architecture?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("Game","ARCHITECTURE","Modular"), expected_evidence=ExpectedEvidence(file="game.py", symbol="Game")),
        GoldenCase(id="battleship_redis_negative", repository="battleship-python", repository_path="eval_repos/battleship-python", question="Does this repository use Redis?", mode="FAST", expected_verdict=Verdict.INSUFFICIENT_EVIDENCE, expected_claim=ExpectedClaim("Application","USES","Redis"), expected_evidence=ExpectedEvidence(file="", symbol="")),
        GoldenCase(id="battleship_spring_negative", repository="battleship-python", repository_path="eval_repos/battleship-python", question="Does this repository use Spring?", mode="FAST", expected_verdict=Verdict.INSUFFICIENT_EVIDENCE, expected_claim=ExpectedClaim("Application","USES","Spring"), expected_evidence=ExpectedEvidence(file="", symbol="")),
        GoldenCase(id="battleship_owner_isolation", repository="battleship-python", repository_path="eval_repos/battleship-python", question="Where is OwnerController?", mode="FAST", expected_verdict=Verdict.INSUFFICIENT_EVIDENCE, expected_claim=ExpectedClaim("OwnerController","DEFINED_IN","OwnerController.java"), expected_evidence=ExpectedEvidence(file="", symbol="")),
        # Cross-system 4
        GoldenCase(id="cross_filename_collision", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="Does battleship-python contain OwnerController?", mode="FAST", expected_verdict=Verdict.INSUFFICIENT_EVIDENCE, expected_claim=ExpectedClaim("OwnerController","DEFINED_IN","OwnerController.java"), expected_evidence=ExpectedEvidence(file="", symbol="")),
        GoldenCase(id="cross_stale_snapshot", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="Does this repository use Kubernetes?", mode="FAST", expected_verdict=Verdict.INSUFFICIENT_EVIDENCE, expected_claim=ExpectedClaim("Application","USES","Kubernetes"), expected_evidence=ExpectedEvidence(file="", symbol="")),
        GoldenCase(id="cross_evidence_resolution", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="Where is OwnerController evidence?", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("OwnerController","DEFINED_IN","OwnerController.java"), expected_evidence=ExpectedEvidence(file="OwnerController.java", symbol="OwnerController")),
        GoldenCase(id="cross_workspace_context", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="Explain OwnerController with workspace context", mode="FAST", expected_verdict=Verdict.VERIFIED, expected_claim=ExpectedClaim("OwnerController","DEFINED_IN","OwnerController.java"), expected_evidence=ExpectedEvidence(file="OwnerController.java", symbol="OwnerController")),
        # AI suggestion cases
        GoldenCase(id="suggestion_pagination", repository="spring-petclinic", repository_path="eval_repos/spring-petclinic", question="How could pagination be added to the owner API?", mode="FAST", expected_verdict=Verdict.AI_SUGGESTION, expected_claim=ExpectedClaim("Pagination","SUGGESTED_FOR","OwnerAPI"), expected_evidence=ExpectedEvidence(file="OwnerController.java", symbol="OwnerController")),
    ]
    # Split into per-repo files + combined
    import json, pathlib
    out = {"dataset_version": "1.0", "cases": [c.to_dict() for c in cases]}
    pathlib.Path("GOLDEN_EVALUATION_DATASET.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    # Also write per-repo
    for repo in ["spring-petclinic", "sp-portfolio", "battleship-python"]:
        rcases = [c for c in cases if c.repository == repo]
        (Path("tests/golden/dataset") / f"{repo}.json").write_text(json.dumps({"cases": [c.to_dict() for c in rcases]}, indent=2), encoding="utf-8")
    # adversarial
    adv = [c for c in cases if "negative" in c.id or "redis" in c.id.lower() or "kafka" in c.id.lower()]
    (Path("tests/golden/dataset") / "adversarial.json").write_text(json.dumps({"cases": [c.to_dict() for c in adv]}, indent=2), encoding="utf-8")
    return cases
