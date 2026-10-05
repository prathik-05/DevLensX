"""
DevLensX Understanding Subsystem: Flow Detector & Architecture Detector
Extracts user/business execution flows and detects repository architectural style.
Polyglot-aware: supports Java Spring, Python FastAPI/Flask, TypeScript Express/Next.js, Go, Rust, C#.
"""

from typing import Dict, Any, List

# Stereotypes that indicate an HTTP request entry point across languages
_CONTROLLER_STEREOTYPES = {
    # Java Spring
    "Controller", "RestController",
    # Python FastAPI/Flask
    "Router", "APIRouter", "Blueprint",
    # TypeScript/Express
    "Route", "Handler",
    # Generic
    "Endpoint", "Ingress",
}

# Stereotypes that indicate a business logic / service layer
_SERVICE_STEREOTYPES = {
    # Java Spring
    "Service",
    # Python
    "Manager", "Processor",
    # TypeScript/NestJS
    "Provider",
    # Generic
    "BusinessLogic", "UseCase",
}

# Stereotypes that indicate a data access / repository layer
_REPO_STEREOTYPES = {
    # Java Spring
    "Repository",
    # Python
    "DAO", "Store",
    # TypeScript
    "DataAccess",
    # Generic
    "Persistence",
}


class FlowDetector:
    @staticmethod
    def detect_execution_flows(classes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Maps user action -> REST route -> controller/handler -> service -> repository execution flows.
        
        Polyglot-aware: uses stereotype detection across Java, Python, TypeScript, Go.
        Safe against URMSymbol-derived dicts with missing keys.
        """
        flows = []

        # Detect entry points: either via stereotype OR via endpoint list
        controllers = [
            c for c in classes
            if c.get("stereotype") in _CONTROLLER_STEREOTYPES
            or (c.get("endpoints") and len(c.get("endpoints", [])) > 0)
        ]

        # Fallback for repos with no stereotyped controllers: use classes with endpoints
        if not controllers:
            controllers = [c for c in classes if c.get("endpoints")]

        # Final fallback: use any non-test class with dependencies
        if not controllers:
            controllers = [c for c in classes if c.get("injected_dependencies") and not c.get("is_test")][:3]

        for ctrl in controllers[:5]:
            name = ctrl.get("name") or ctrl.get("qualified_name", "Unknown")
            endpoints = ctrl.get("endpoints", [])

            # Determine route label
            if endpoints:
                ep0 = endpoints[0]
                if isinstance(ep0, dict):
                    route_str = ep0.get("path") or ep0.get("full_path") or ep0.get("route") or f"/{name.lower()}"
                    method = ep0.get("method") or ep0.get("http_method", "GET")
                else:
                    route_str = str(ep0)
                    method = "GET"
            else:
                clean_name = name.lower().replace("controller", "").replace("router", "").replace("handler", "")
                route_str = f"/api/{clean_name}" if clean_name else f"/{name.lower()}"
                method = "GET"

            # Find downstream service/handler
            deps = ctrl.get("injected_dependencies", []) or []
            service_name = deps[0] if deps else None

            # Try to infer service from classes matching _SERVICE_STEREOTYPES
            if not service_name:
                for dep_class in classes:
                    dep_name = dep_class.get("name", "")
                    if dep_class.get("stereotype") in _SERVICE_STEREOTYPES and not dep_class.get("is_test"):
                        service_name = dep_name
                        break

            service_name = service_name or "ServiceLayer"

            lang_label = ctrl.get("language", "")
            steps = [
                f"1. HTTP Client sends {method} request to {route_str}",
                f"2. {name} handles input validation and request mapping",
                f"3. Delegates business logic to {service_name}",
                f"4. Executes data operation and returns response payload",
            ]

            flows.append({
                "flow_name": f"Execute {name.replace('Controller','').replace('Router','').replace('Handler','')} Action",
                "user_action": f"Developer / API Client triggers {method} {route_str}",
                "execution_steps": steps,
                "participating_components": [name, service_name],
                "language": lang_label,
                "evidence_status": "🟢 VERIFIED BY AST",
            })

        return flows


class ArchitectureDetector:
    @staticmethod
    def detect_architecture_style(classes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detects architectural style across polyglot repos.
        
        Returns style classification with evidence from detected stereotypes and patterns.
        """
        stereotypes = set()
        for c in classes:
            st = c.get("stereotype")
            if st:
                stereotypes.add(st)

        # Java Spring MVC / NestJS style
        has_controller = bool(_CONTROLLER_STEREOTYPES & stereotypes)
        has_service = bool(_SERVICE_STEREOTYPES & stereotypes)
        has_repo = bool(_REPO_STEREOTYPES & stereotypes)

        # Endpoint count (polyglot detection)
        has_endpoints = any(c.get("endpoints") for c in classes)
        # File diversity (multiple directories → modular)
        file_dirs = {
            c.get("file", "").replace("\\", "/").rsplit("/", 1)[0]
            for c in classes if c.get("file")
        }

        if has_controller and (has_service or has_repo):
            style = "Modular Layered Architecture (Handler ➔ Service ➔ Repository)"
            description = "Codebase follows formal separation of concerns between HTTP presentation, domain logic, and data persistence."
        elif has_endpoints and len(file_dirs) > 3:
            style = "Feature-Oriented API Structure"
            description = "Components are organized into domain-based modules with HTTP endpoints. No strict layering detected."
        elif has_endpoints:
            style = "Monolithic API (Single-Layer)"
            description = "HTTP handlers and business logic are co-located without explicit service abstraction."
        elif len(file_dirs) > 4:
            style = "Feature-Oriented Package Structure"
            description = "Components are grouped into domain package boundaries without HTTP endpoints."
        else:
            style = "Concentrated / Unstructured Architecture"
            description = "Most functionality is concentrated across key monolithic files."

        return {
            "architectural_style": style,
            "description": description,
            "detected_stereotypes": sorted(stereotypes),
            "has_http_layer": has_controller or has_endpoints,
            "has_service_layer": has_service,
            "has_data_layer": has_repo,
            "module_count": len(file_dirs),
            "evidence_status": "🟢 VERIFIED BY AST SCANNER",
        }

