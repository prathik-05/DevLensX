"""
TRUE POSITIVE FRR (FALSE REJECTION RATE) VERIFICATION
Tests the post-fix CriticAgent directly against the 29 Ground-Truth True Positive findings
from the paper benchmark dataset across Spring Petclinic, MyBatis-3, and Apache Dubbo.
Confirms whether FRR remains strictly 0.0% (0/29 false rejections).
"""

import sys, os
sys.path.insert(0, os.getcwd())

from devlensx.parser import parse_repo
from devlensx.graph import KuzuGraphStore
from devlensx.agents import ArchitectureAgent, SecurityAgent, ChangeImpactAgent
from devlensx.critic import CriticAgent

print("=" * 85)
print("GROUND-TRUTH TRUE POSITIVE FALSE REJECTION RATE (FRR) VERIFICATION")
print("=" * 85)

tp_datasets = [
    ("Spring PetClinic", "eval_repos/spring-petclinic", "tp_petclinic", [
        {"agent": "ArchitectureAgent", "category": "Coupling", "title": "High Coupling Bottleneck: VetRepository", "severity": "MEDIUM", "class_name": "VetRepository", "file": "src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java", "claim": "VetRepository is directly depended on by 3 components.", "evidence": {"incoming_dependents": 3, "stereotype": "Repository"}},
        {"agent": "ArchitectureAgent", "category": "Coupling", "title": "High Coupling Bottleneck: OwnerRepository", "severity": "MEDIUM", "class_name": "OwnerRepository", "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerRepository.java", "claim": "OwnerRepository is directly depended on by 4 components.", "evidence": {"incoming_dependents": 4, "stereotype": "Repository"}},
        {"agent": "ArchitectureAgent", "category": "Coupling", "title": "High Coupling Bottleneck: PetTypeRepository", "severity": "MEDIUM", "class_name": "PetTypeRepository", "file": "src/main/java/org/springframework/samples/petclinic/owner/PetTypeRepository.java", "claim": "PetTypeRepository is directly depended on by 3 components.", "evidence": {"incoming_dependents": 3, "stereotype": "Repository"}},
        {"agent": "SecurityAgent", "category": "API Security", "title": "Unprotected REST Endpoint: GetMapping /owners/new", "severity": "MEDIUM", "class_name": "OwnerController", "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java", "claim": "Endpoint /owners/new in controller OwnerController does not specify explicit authorization annotations.", "evidence": {"endpoint": "/owners/new", "controller": "OwnerController"}},
        {"agent": "SecurityAgent", "category": "API Security", "title": "Unprotected REST Endpoint: PostMapping /owners/new", "severity": "MEDIUM", "class_name": "OwnerController", "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java", "claim": "Endpoint /owners/new in controller OwnerController does not specify explicit authorization annotations.", "evidence": {"endpoint": "/owners/new", "controller": "OwnerController"}},
        {"agent": "SecurityAgent", "category": "API Security", "title": "Unprotected REST Endpoint: GetMapping /owners/find", "severity": "MEDIUM", "class_name": "OwnerController", "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java", "claim": "Endpoint /owners/find in controller OwnerController does not specify explicit authorization annotations.", "evidence": {"endpoint": "/owners/find", "controller": "OwnerController"}},
        {"agent": "ChangeImpactAgent", "category": "Change Impact", "title": "High Blast-Radius Risk: Modifying VetRepository", "severity": "HIGH", "class_name": "VetRepository", "file": "src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java", "claim": "Modifying VetRepository affects 3 downstream components.", "evidence": {"incoming_dependents": 3}},
        {"agent": "ChangeImpactAgent", "category": "Change Impact", "title": "High Blast-Radius Risk: Modifying OwnerRepository", "severity": "HIGH", "class_name": "OwnerRepository", "file": "src/main/java/org/springframework/samples/petclinic/owner/OwnerRepository.java", "claim": "Modifying OwnerRepository affects 4 downstream components.", "evidence": {"incoming_dependents": 4}},
    ]),

    ("MyBatis 3", "eval_repos/mybatis-3", "tp_mybatis", [
        {"agent": "ArchitectureAgent", "category": "Maintainability", "title": "High Complexity God Class Detected: MappedStatement", "severity": "HIGH", "class_name": "MappedStatement", "file": "src/main/java/org/apache/ibatis/mapping/MappedStatement.java", "claim": "MappedStatement contains 42 methods, violating single responsibility principles.", "evidence": {"method_count": 42, "stereotype": "Other"}},
        {"agent": "ArchitectureAgent", "category": "Maintainability", "title": "High Complexity God Class Detected: Configuration", "severity": "HIGH", "class_name": "Configuration", "file": "src/main/java/org/apache/ibatis/session/Configuration.java", "claim": "Configuration contains 98 methods, violating single responsibility principles.", "evidence": {"method_count": 98, "stereotype": "Configuration"}},
        {"agent": "ArchitectureAgent", "category": "Maintainability", "title": "High Complexity God Class Detected: MetaObject", "severity": "HIGH", "class_name": "MetaObject", "file": "src/main/java/org/apache/ibatis/reflection/MetaObject.java", "claim": "MetaObject contains 31 methods, violating single responsibility principles.", "evidence": {"method_count": 31, "stereotype": "Other"}},
        {"agent": "ArchitectureAgent", "category": "Maintainability", "title": "High Complexity God Class Detected: SqlSession", "severity": "HIGH", "class_name": "SqlSession", "file": "src/main/java/org/apache/ibatis/session/SqlSession.java", "claim": "SqlSession contains 24 methods, violating single responsibility principles.", "evidence": {"method_count": 24, "stereotype": "Other"}},
        {"agent": "ArchitectureAgent", "category": "Maintainability", "title": "High Complexity God Class Detected: TypeHandlerRegistry", "severity": "HIGH", "class_name": "TypeHandlerRegistry", "file": "src/main/java/org/apache/ibatis/type/TypeHandlerRegistry.java", "claim": "TypeHandlerRegistry contains 46 methods, violating single responsibility principles.", "evidence": {"method_count": 46, "stereotype": "Other"}},
        {"agent": "ArchitectureAgent", "category": "Coupling", "title": "High Coupling Bottleneck: Configuration", "severity": "MEDIUM", "class_name": "Configuration", "file": "src/main/java/org/apache/ibatis/session/Configuration.java", "claim": "Configuration is directly depended on by 35 components.", "evidence": {"incoming_dependents": 35, "stereotype": "Configuration"}},
        {"agent": "ArchitectureAgent", "category": "Coupling", "title": "High Coupling Bottleneck: ObjectFactory", "severity": "MEDIUM", "class_name": "ObjectFactory", "file": "src/main/java/org/apache/ibatis/reflection/factory/ObjectFactory.java", "claim": "ObjectFactory is directly depended on by 8 components.", "evidence": {"incoming_dependents": 8, "stereotype": "Other"}},
        {"agent": "ChangeImpactAgent", "category": "Change Impact", "title": "High Blast-Radius Risk: Modifying Configuration", "severity": "HIGH", "class_name": "Configuration", "file": "src/main/java/org/apache/ibatis/session/Configuration.java", "claim": "Modifying Configuration affects 35 downstream components.", "evidence": {"incoming_dependents": 35}},
        {"agent": "ChangeImpactAgent", "category": "Change Impact", "title": "High Blast-Radius Risk: Modifying ObjectFactory", "severity": "HIGH", "class_name": "ObjectFactory", "file": "src/main/java/org/apache/ibatis/reflection/factory/ObjectFactory.java", "claim": "Modifying ObjectFactory affects 8 downstream components.", "evidence": {"incoming_dependents": 8}},
    ]),

    ("Apache Dubbo", "eval_repos/dubbo", "tp_dubbo", [
        {"agent": "ArchitectureAgent", "category": "Maintainability", "title": "High Complexity God Class Detected: DubboConfigurationProperties", "severity": "HIGH", "class_name": "DubboConfigurationProperties", "file": "dubbo-config/dubbo-config-spring/src/main/java/org/apache/dubbo/config/spring/context/properties/DubboConfigurationProperties.java", "claim": "DubboConfigurationProperties contains 38 methods.", "evidence": {"method_count": 38, "stereotype": "Configuration"}},
        {"agent": "ArchitectureAgent", "category": "Coupling", "title": "High Coupling Bottleneck: Invoker", "severity": "MEDIUM", "class_name": "Invoker", "file": "dubbo-rpc/dubbo-rpc-api/src/main/java/org/apache/dubbo/rpc/Invoker.java", "claim": "Invoker is directly depended on by 20 components.", "evidence": {"incoming_dependents": 20, "stereotype": "Service"}},
        {"agent": "ArchitectureAgent", "category": "Coupling", "title": "High Coupling Bottleneck: RegistryDirectory", "severity": "MEDIUM", "class_name": "RegistryDirectory", "file": "dubbo-registry/dubbo-registry-api/src/main/java/org/apache/dubbo/registry/integration/RegistryDirectory.java", "claim": "RegistryDirectory is directly depended on by 12 components.", "evidence": {"incoming_dependents": 12, "stereotype": "Service"}},
        {"agent": "ArchitectureAgent", "category": "Coupling", "title": "High Coupling Bottleneck: ZookeeperRegistry", "severity": "MEDIUM", "class_name": "ZookeeperRegistry", "file": "dubbo-registry/dubbo-registry-zookeeper/src/main/java/org/apache/dubbo/registry/zookeeper/ZookeeperRegistry.java", "claim": "ZookeeperRegistry is directly depended on by 8 components.", "evidence": {"incoming_dependents": 8, "stereotype": "Repository"}},
        {"agent": "SecurityAgent", "category": "API Security", "title": "Unprotected REST Endpoint: GetMapping /dubbo/providers", "severity": "MEDIUM", "class_name": "DubboProtocol", "file": "dubbo-rpc/dubbo-rpc-dubbo/src/main/java/org/apache/dubbo/rpc/protocol/dubbo/DubboProtocol.java", "claim": "Endpoint /dubbo/providers in controller DubboProtocol does not specify explicit authorization annotations.", "evidence": {"endpoint": "/dubbo/providers", "controller": "DubboProtocol"}},
        {"agent": "ChangeImpactAgent", "category": "Change Impact", "title": "High Blast-Radius Risk: Modifying Invoker", "severity": "HIGH", "class_name": "Invoker", "file": "dubbo-rpc/dubbo-rpc-api/src/main/java/org/apache/dubbo/rpc/Invoker.java", "claim": "Modifying Invoker affects 20 downstream components.", "evidence": {"incoming_dependents": 20}},
        {"agent": "ChangeImpactAgent", "category": "Change Impact", "title": "High Blast-Radius Risk: Modifying RegistryDirectory", "severity": "HIGH", "class_name": "RegistryDirectory", "file": "dubbo-registry/dubbo-registry-api/src/main/java/org/apache/dubbo/registry/integration/RegistryDirectory.java", "claim": "Modifying RegistryDirectory affects 12 downstream components.", "evidence": {"incoming_dependents": 12}},
        {"agent": "ChangeImpactAgent", "category": "Change Impact", "title": "High Blast-Radius Risk: Modifying ZookeeperRegistry", "severity": "HIGH", "class_name": "ZookeeperRegistry", "file": "dubbo-registry/dubbo-registry-zookeeper/src/main/java/org/apache/dubbo/registry/zookeeper/ZookeeperRegistry.java", "claim": "Modifying ZookeeperRegistry affects 8 downstream components.", "evidence": {"incoming_dependents": 8}},
        {"agent": "ArchitectureAgent", "category": "Maintainability", "title": "High Complexity God Class Detected: URL", "severity": "HIGH", "class_name": "URL", "file": "dubbo-common/src/main/java/org/apache/dubbo/common/URL.java", "claim": "URL contains 75 methods.", "evidence": {"method_count": 75, "stereotype": "Other"}},
        {"agent": "ArchitectureAgent", "category": "Maintainability", "title": "High Complexity God Class Detected: RpcContext", "severity": "HIGH", "class_name": "RpcContext", "file": "dubbo-rpc/dubbo-rpc-api/src/main/java/org/apache/dubbo/rpc/RpcContext.java", "claim": "RpcContext contains 50 methods.", "evidence": {"method_count": 50, "stereotype": "Other"}},
        {"agent": "ArchitectureAgent", "category": "Maintainability", "title": "High Complexity God Class Detected: ExtensionLoader", "severity": "HIGH", "class_name": "ExtensionLoader", "file": "dubbo-common/src/main/java/org/apache/dubbo/common/extension/ExtensionLoader.java", "claim": "ExtensionLoader contains 62 methods.", "evidence": {"method_count": 62, "stereotype": "Other"}},
        {"agent": "ChangeImpactAgent", "category": "Change Impact", "title": "High Blast-Radius Risk: Modifying URL", "severity": "HIGH", "class_name": "URL", "file": "dubbo-common/src/main/java/org/apache/dubbo/common/URL.java", "claim": "Modifying URL affects 45 downstream components.", "evidence": {"incoming_dependents": 45}}
    ])
]

total_tp_count = 0
total_tp_verified = 0
total_tp_rejected = 0

for name, path, db_name, tps in tp_datasets:
    if not os.path.exists(path):
        continue
    print(f"\n[+] EVALUATING TRUE POSITIVES FOR: {name} (N={len(tps)})")
    model = parse_repo(path)
    graph = KuzuGraphStore(db_path=f"tp_bench_{db_name}")
    graph.build_from_model(model)
    critic = CriticAgent(graph)

    results = critic.verify_all(tps, model)
    v_cnt = sum(1 for r in results if r["verdict"] == "VERIFIED")
    r_cnt = sum(1 for r in results if r["verdict"] == "REJECTED")

    total_tp_count += len(tps)
    total_tp_verified += v_cnt
    total_tp_rejected += r_cnt

    print(f"    - True Positives Evaluated: {len(tps)}")
    print(f"    - VERIFIED by Post-Fix Critic: {v_cnt}")
    print(f"    - REJECTED by Post-Fix Critic: {r_cnt}")
    for r in results:
        status = "[OK] VERIFIED" if r["verdict"] == "VERIFIED" else "[X] REJECTED"
        print(f"      {status:14s} [{r['evidence_coverage_score']:5.1f}% ({r['evidence_ratio']})] {r['title']}")

print("\n" + "=" * 85)
print("TRUE POSITIVE FALSE REJECTION RATE (FRR) SUMMARY")
print("=" * 85)
print(f"Total Ground-Truth True Positives Evaluated: {total_tp_count}")
print(f"Total True Positives Verified by Critic:     {total_tp_verified}")
print(f"Total True Positives Rejected by Critic:     {total_tp_rejected}")
frr = round((total_tp_rejected / max(1, total_tp_count)) * 100, 2)
print(f"FALSE REJECTION RATE (FRR):                   {frr}% ({total_tp_rejected}/{total_tp_count})")
print("=" * 85)
