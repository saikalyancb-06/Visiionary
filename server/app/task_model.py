"""
General Task Model for Visiionary Autonomous Browser Agent.

Represents arbitrary user tasks independently from any specific website, domain,
or category.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

INTENT_FIND_INFO = 'FIND_INFORMATION'
INTENT_NAVIGATE_RESOURCE = 'NAVIGATE_RESOURCE'
INTENT_SELECT_ENTITY = 'SELECT_ENTITY'
INTENT_DOWNLOAD_ARTIFACT = 'DOWNLOAD_ARTIFACT'
INTENT_FILL_FORM = 'FILL_FORM'
INTENT_TRANSACTION = 'EXECUTE_TRANSACTION'
INTENT_COMPARE = 'COMPARE_RECORDS'
INTENT_GENERIC = 'GENERIC_INTERACTION'

POST_TARGET_OPENED = 'TARGET_OPENED'
POST_TARGET_SELECTED = 'TARGET_SELECTED'
POST_ARTIFACT_DOWNLOADED = 'ARTIFACT_DOWNLOADED'
POST_FORM_SUBMITTED = 'FORM_SUBMITTED'
POST_COLLECTION_UPDATED = 'COLLECTION_UPDATED'
POST_INFORMATION_FOUND = 'INFORMATION_FOUND'
POST_RESOURCE_REACHED = 'RESOURCE_REACHED'

CRITERIA_PATTERNS = [
    (re.compile(r'\b(best\s*seller|best-selling|best\s*selling|top\s*seller|top-selling)\b', re.I), 'BEST_SELLING', 'best seller'),
    (re.compile(r'\b(highest\s*rated|top\s*rated|top-rated|best\s*rated|best-reviewed)\b', re.I), 'HIGHEST_RATED', 'highest rated'),
    (re.compile(r'\b(most\s*popular|trending|popular)\b', re.I), 'MOST_POPULAR', 'most popular'),
    (re.compile(r'\b(cheapest|lowest\s*priced|lowest\s*price|most\s*affordable)\b', re.I), 'LOWEST_PRICED', 'cheapest'),
    (re.compile(r'\b(highest\s*priced|most\s*expensive)\b', re.I), 'HIGHEST_PRICED', 'highest priced'),
    (re.compile(r'\b(newest|latest|new\s*arrival)\b', re.I), 'NEWEST', 'newest'),
]

COLOR_LEXICON = {
    'black', 'white', 'blue', 'red', 'green', 'yellow', 'pink', 'purple', 'orange',
    'brown', 'grey', 'gray', 'navy', 'beige', 'maroon', 'teal', 'silver', 'gold',
    'olive', 'cyan', 'magenta', 'violet', 'indigo', 'turquoise', 'charcoal', 'cream',
    'tan', 'khaki', 'burgundy', 'crimson', 'emerald', 'coral', 'peach', 'lavender'
}

GENDER_CATEGORY_LEXICON = {
    'men': 'men', 'mens': 'men', "men's": 'men',
    'women': 'women', 'womens': 'women', "women's": 'women',
    'kids': 'kids', 'boys': 'boys', 'girls': 'girls', 'unisex': 'unisex'
}

MATERIAL_LEXICON = {
    'cotton', 'leather', 'denim', 'silk', 'wool', 'linen', 'polyester', 'nylon',
    'canvas', 'velvet', 'satin', 'fleece', 'metal', 'wood', 'glass', 'plastic', 'ceramic'
}

@dataclass
class GeneralTaskModel:
    raw_task: str
    intent_type: str = INTENT_GENERIC
    objective: str = ''
    target_type: str = 'unknown'
    hard_constraints: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    selection_criterion: Optional[str] = None
    selection_criterion_label: Optional[str] = None
    requested_actions: List[str] = field(default_factory=list)
    required_postconditions: List[str] = field(default_factory=list)
    prerequisites: Dict[str, Any] = field(default_factory=dict)
    unresolved_requirements: List[str] = field(default_factory=list)
    search_query: Optional[str] = None
    # Dependency-aware state machine requirements
    required_candidate_count: int = 1
    requires_comparison: bool = False
    requires_information_extraction: bool = False
    information_fields_requested: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'raw_task': self.raw_task,
            'intent_type': self.intent_type,
            'objective': self.objective,
            'target_type': self.target_type,
            'hard_constraints': self.hard_constraints,
            'preferences': self.preferences,
            'selection_criterion': self.selection_criterion,
            'selection_criterion_label': self.selection_criterion_label,
            'requested_actions': self.requested_actions,
            'required_postconditions': self.required_postconditions,
            'prerequisites': self.prerequisites,
            'unresolved_requirements': self.unresolved_requirements,
            'search_query': self.search_query,
            'required_candidate_count': self.required_candidate_count,
            'requires_comparison': self.requires_comparison,
            'requires_information_extraction': self.requires_information_extraction,
            'information_fields_requested': self.information_fields_requested,
        }

def parse_general_task(task_str: str) -> GeneralTaskModel:
    task_clean = (task_str or '').strip()
    t_lower = task_clean.lower()
    tokens = [w for w in re.split(r'[^a-zA-Z0-9]+', t_lower) if len(w) > 1]
    tokens_set = set(tokens)

    criterion = None
    criterion_label = None
    for pattern, c_name, disp in CRITERIA_PATTERNS:
        if pattern.search(t_lower):
            criterion = c_name
            criterion_label = disp
            break

    requested_actions: List[str] = []
    required_postconditions: List[str] = []

    nav_match = re.search(r'(?:open|go to|navigate to|visit)\s+([a-zA-Z0-9\s._-]+?)(?:\s+(?:and|then|to|for)\s+|$)', task_clean, re.I)
    target_site = None
    if nav_match:
        cand_site = nav_match.group(1).strip()
        clean_site = re.sub(r'^(the|a|an)\s+', '', cand_site, flags=re.I).strip()
        if clean_site.lower() not in ('it', 'the', 'page', 'item', 'product', 'details', 'selected'):
            target_site = clean_site
            requested_actions.append(f'NAVIGATE:{target_site}')
            required_postconditions.append(POST_RESOURCE_REACHED)

    search_match = re.search(r'(?:search for|find|search|look for|query)\s+["\']?([^"\']+)["\']?', task_clean, re.I)
    search_query = None
    if search_match:
        raw_q = search_match.group(1).strip()
        raw_q = re.sub(r'\s+(?:inside|in|on)\s+(?:that|the|this)?\s*(?:website|portal|page|site|store|app).*$', '', raw_q, flags=re.I)
        raw_q = re.sub(r'\s+(?:and|then|to)\s+(?:open|add|buy|view|download|cart|submit).*$', '', raw_q, flags=re.I)
        search_query = raw_q.strip()
        requested_actions.append(f'SEARCH:{search_query}')

    if re.search(r'\b(add\s+to\s+cart|add\s+it\s+to\s+cart|add\s+to\s+basket|cart|buy\s+now|buy|purchase)\b', t_lower):
        requested_actions.append('ADD_TO_CART')
        required_postconditions.append(POST_COLLECTION_UPDATED)
    elif re.search(r'\b(download|export|save\s+pdf|get\s+pdf|save\s+document)\b', t_lower):
        requested_actions.append('DOWNLOAD')
        required_postconditions.append(POST_ARTIFACT_DOWNLOADED)
    elif re.search(r'\b(submit|apply|confirm|book|reserve|checkout|proceed)\b', t_lower):
        requested_actions.append('SUBMIT')
        required_postconditions.append(POST_FORM_SUBMITTED)
    elif re.search(r'\b(open\s+it|open\s+product|open\s+the\s+selected|open\s+item|view\s+details|select)\b', t_lower):
        requested_actions.append('SELECT_ENTITY')
        required_postconditions.append(POST_TARGET_OPENED)
    else:
        if search_query or target_site:
            required_postconditions.append(POST_INFORMATION_FOUND)

    if 'DOWNLOAD' in requested_actions:
        intent_type = INTENT_DOWNLOAD_ARTIFACT
    elif 'ADD_TO_CART' in requested_actions:
        intent_type = INTENT_TRANSACTION
    elif 'SUBMIT' in requested_actions:
        intent_type = INTENT_FILL_FORM
    elif 'SELECT_ENTITY' in requested_actions:
        intent_type = INTENT_SELECT_ENTITY
    elif any(a.startswith('SEARCH:') for a in requested_actions):
        intent_type = INTENT_FIND_INFO
    elif target_site:
        intent_type = INTENT_NAVIGATE_RESOURCE
    else:
        intent_type = INTENT_GENERIC

    hard_constraints: Dict[str, Any] = {}
    prerequisites: Dict[str, Any] = {}

    for tok in tokens:
        if tok in COLOR_LEXICON and 'color' not in hard_constraints:
            hard_constraints['color'] = tok
            break

    for tok in tokens:
        if tok in GENDER_CATEGORY_LEXICON and 'gender' not in hard_constraints:
            hard_constraints['gender'] = GENDER_CATEGORY_LEXICON[tok]
            break

    for tok in tokens:
        if tok in MATERIAL_LEXICON and 'material' not in hard_constraints:
            hard_constraints['material'] = tok
            break

    size_m = re.search(r'\b(?:size|sz)\s+([a-zA-Z0-9]+)\b', t_lower)
    if size_m:
        hard_constraints['size'] = size_m.group(1).lower()
        prerequisites['size'] = size_m.group(1).lower()

    id_m = re.search(r'\b(?:problem statement|ps|item|number|no\.?|id|code|case|order)\s*([0-9]{2,6})\b', t_lower)
    if id_m:
        hard_constraints['item_id'] = id_m.group(1)

    target_type = 'unknown'
    if any(k in t_lower for k in ('shirt', 't-shirt', 'shoes', 'jacket', 'pants', 'dress', 'clothing', 'item', 'product')):
        target_type = 'product'
        for pt in ('t-shirt', 'shirt', 'shoe', 'shoes', 'jacket', 'pants', 'dress', 'hoodie', 'watch', 'laptop', 'phone'):
            if pt in tokens_set or any(pt in tok for tok in tokens_set):
                hard_constraints['product_type'] = pt
                break
    elif any(k in t_lower for k in ('problem statement', 'paper', 'document', 'pdf', 'report', 'manual', 'guide', 'statement', 'invoice')):
        target_type = 'document'
        if 'item_id' in hard_constraints:
            hard_constraints['document_id'] = hard_constraints['item_id']
    elif any(k in t_lower for k in ('form', 'application', 'survey', 'registration')):
        target_type = 'form'
    elif any(k in t_lower for k in ('account', 'login', 'password', 'profile')):
        target_type = 'account'
    elif any(k in t_lower for k in ('article', 'news', 'post', 'blog', 'wiki')):
        target_type = 'article'

    unresolved: List[str] = []
    if criterion and not hard_constraints.get('selection_evidence'):
        unresolved.append(f'SELECTION_EVIDENCE:{criterion}')
    if target_type == 'product' and 'size' not in hard_constraints and 'ADD_TO_CART' in requested_actions:
        unresolved.append('PREREQUISITE_CHECK:size_option')

    # Parse dependency-aware state machine requirements
    from server.app.task_state_machine import parse_task_requirements as _parse_reqs
    _reqs = _parse_reqs(task_clean)

    return GeneralTaskModel(
        raw_task=task_clean,
        intent_type=intent_type,
        objective=task_clean,
        target_type=target_type,
        hard_constraints=hard_constraints,
        selection_criterion=criterion,
        selection_criterion_label=criterion_label,
        requested_actions=requested_actions,
        required_postconditions=required_postconditions,
        prerequisites=prerequisites,
        unresolved_requirements=unresolved,
        search_query=search_query,
        required_candidate_count=_reqs["required_candidate_count"],
        requires_comparison=_reqs["requires_comparison"],
        requires_information_extraction=_reqs["requires_information_extraction"],
        information_fields_requested=_reqs["information_fields_requested"],
    )

