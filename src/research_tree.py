"""
Dynamic Knowledge Tree inspired by CTree/ChatIndex.
Allows the agent to classify and store learned information hierarchically.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from uuid import uuid4

@dataclass
class KnowledgeNode:
    id: str
    topic: str  # The "Tag" or "Class" assigned by the Agent
    content: str # The learned fact or summary
    source_url: Optional[str] = None
    children: List['KnowledgeNode'] = field(default_factory=list)
    parent_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "content": self.content,
            "source_url": self.source_url,
            "children": [c.to_dict() for c in self.children]
        }

class ResearchTree:
    """
    A dynamic tree where the agent stores its 'Baules' (Buckets) of knowledge.
    """
    def __init__(self):
        self.root = KnowledgeNode(id="root", topic="Research Goal", content="Root of the investigation")
        self.node_map: Dict[str, KnowledgeNode] = {"root": self.root}

    def add_node(self, parent_id: str, topic: str, content: str, source_url: str = None) -> str:
        """
        The agent calls this to store a new finding.
        Example: add_node("root", "Beethoven Biography", "Born in Bonn in 1770...")
        """
        if parent_id not in self.node_map:
            raise ValueError(f"Parent node {parent_id} not found.")
        
        new_id = str(uuid4())[:8]
        new_node = KnowledgeNode(id=new_id, topic=topic, content=content, source_url=source_url, parent_id=parent_id)
        
        parent_node = self.node_map[parent_id]
        parent_node.children.append(new_node)
        self.node_map[new_id] = new_node
        
        return new_id

    def get_tree_view(self, node: Optional[KnowledgeNode] = None, depth: int = 0) -> str:
        """
        Returns a text representation of the tree STRUCTURE (Topics/IDs only).
        This allows the LLM to see what it knows without reading all content.
        """
        if node is None:
            node = self.root
            
        # Don't show root content, just structure
        output = "  " * depth + f"- [{node.id}] {node.topic}"
        if depth == 0:
            output = f"KNOWLEDGE TREE:\n{output}"
            
        for child in node.children:
            output += "\n" + self.get_tree_view(child, depth + 1)
            
        return output

    def get_node_content(self, node_id: str) -> str:
        """Allows the agent to 'Zoom In' on a specific memory bucket."""
        if node_id not in self.node_map:
            return "Node not found."
        node = self.node_map[node_id]
        return f"TOPIC: {node.topic}\nSOURCE: {node.source_url}\nCONTENT:\n{node.content}"

    def to_json(self) -> str:
        return json.dumps(self.root.to_dict(), indent=2)