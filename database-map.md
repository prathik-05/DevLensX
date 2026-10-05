# Database Architecture & Graph Schemas — DevLensX

> **Detailed Schemas for KuzuDB Embedded Property Graph, FAISS Vector Index, and Benchmark Datasets**

---

## 1. KuzuDB Embedded Property Graph Schema (`devlensx/graph/kuzu_store.py`)

DevLensX initializes an embedded C++ KuzuDB database inside `.devlensx-runtime/kuzu_db/`.

### Node Table: `JavaClass`

| Property Field | Data Type | Primary Key | Description & Example |
| :--- | :--- | :--- | :--- |
| `name` | `STRING` | **Yes** | Fully qualified or simple class name (e.g., `OwnerController`). |
| `stereotype` | `STRING` | No | Architectural category: `Controller`, `Service`, `Repository`, `Entity`, `Configuration`, `Test`, `Other`. |
| `package` | `STRING` | No | Java package namespace (e.g., `org.springframework.samples.petclinic.owner`). |
| `file` | `STRING` | No | File path on disk (e.g., `src/main/java/org/springframework/.../OwnerController.java`). |
| `is_test` | `BOOLEAN` | No | Flag indicating if component is a unit/integration test. |
| `incoming_count`| `INT64` | No | Number of incoming caller dependency edges. |
| `outgoing_count`| `INT64` | No | Number of outgoing dependency edges. |

---

### Relational Edge Tables

#### 1. Edge: `DEPENDS_ON`
* **From:** `JavaClass` (Caller Component)
* **To:** `JavaClass` (Dependency Target)
* **Properties:** None
* **Description:** Represents field injection (`@Autowired`), constructor injection, or direct method invocation.

#### 2. Edge: `EXTENDS`
* **From:** `JavaClass` (Subclass)
* **To:** `JavaClass` (Superclass)
* **Properties:** None
* **Description:** Represents OOP class inheritance (`class PetController extends BaseController`).

#### 3. Edge: `IMPLEMENTS`
* **From:** `JavaClass` (Implementation Class)
* **To:** `JavaClass` (Interface)
* **Properties:** None
* **Description:** Represents interface implementation (`class OwnerRepositoryImpl implements OwnerRepository`).

---

## 2. FAISS Vector Search Schema (`devlensx/retrieval/faiss_retriever.py`)

* **Embedding Model Dimension:** 384-dimensional dense vector space (using lightweight sentence transformers or TF-IDF vector embeddings).
* **Indexed Payload:**
  - `class_name`: Target component name.
  - `stereotype`: Component category.
  - `file`: Path to source file.
  - `snippet`: Formatted textual summary combining class signatures, methods, and fields.

---

## 3. Ground-Truth Benchmark Dataset Schemas (`eval_dataset_*.json`)

DevLensX maintains locked benchmark evaluation JSON files:
- `eval_dataset_spring-petclinic.json` (N=23 findings)
- `eval_dataset_mybatis-3.json` (N=25 findings)
- `eval_dataset_dubbo.json` (N=25 findings)

### Item Schema in Benchmark Files:

```json
{
  "id": "PET-001",
  "title": "High Coupling in OwnerController",
  "claim": "OwnerController has 8 injected dependencies violating coupling threshold.",
  "category": "Coupling",
  "class_name": "OwnerController",
  "file": "org/springframework/samples/petclinic/owner/OwnerController.java",
  "pre_fix_verdict": "VERIFIED",
  "manual_ground_truth_label": "TRUE_POSITIVE"
}
```
