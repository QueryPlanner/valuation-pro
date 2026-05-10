import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict


class XBRLParser:
    """
    A simple parser for XBRL XML files to extract financial data
    without complex business logic.
    """

    def __init__(self, file_path: str | Path):
        self.file_path = str(file_path)
        self.tree = ET.parse(self.file_path)
        self.root = self.tree.getroot()

        # Standard XBRL instance namespace
        self.namespaces = {
            "xbrli": "http://www.xbrl.org/2003/instance",
            "xbrldi": "http://xbrl.org/2006/xbrldi",
        }

    def _extract_contexts(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract all contexts mapping context ID to period details and dimensions.
        """
        contexts = {}
        for context in self.root.findall("xbrli:context", self.namespaces):
            ctx_id = context.attrib.get("id")
            if not ctx_id:
                continue

            period = context.find("xbrli:period", self.namespaces)
            if period is None:
                continue

            start = period.find("xbrli:startDate", self.namespaces)
            end = period.find("xbrli:endDate", self.namespaces)
            instant = period.find("xbrli:instant", self.namespaces)

            # Extract dimensions (segments and scenarios)
            dimensions = {}

            def _extract_dims(container):
                if container is not None:
                    for em in container.findall("xbrldi:explicitMember", self.namespaces):
                        d_attr = em.attrib.get("dimension")
                        if d_attr and em.text:
                            dimensions[d_attr.split(":")[-1]] = em.text.split(":")[-1]

            entity = context.find("xbrli:entity", self.namespaces)
            _extract_dims(entity.find("xbrli:segment", self.namespaces) if entity is not None else None)
            _extract_dims(context.find("xbrli:scenario", self.namespaces))

            context_info = {"dimensions": dimensions}

            if start is not None and end is not None and start.text and end.text:
                period_str = f"{start.text} to {end.text}"
                context_info.update(
                    {
                        "type": "duration",
                        "start": start.text,
                        "end": end.text,
                        "period_str": period_str,
                    }
                )
                contexts[ctx_id] = context_info
            elif instant is not None and instant.text:
                period_str = f"instant {instant.text}"
                context_info.update(
                    {
                        "type": "instant",
                        "instant": instant.text,
                        "period_str": period_str,
                    }
                )
                contexts[ctx_id] = context_info

        return contexts

    def parse(self) -> Dict[str, Dict[str, Any]]:
        """
        Parses the XBRL file and returns a structured dictionary.
        Data is grouped by the resolved time period string.

        Returns:
            Dict[str, Dict[str, Any]]:
            Example:
            {
                "2025-01-01 to 2025-03-31": {
                    "RevenueFromOperations": 1000000,
                    "ProfitBeforeTax": 50000
                },
                "instant 2025-03-31": {
                    "Assets": 5000000
                }
            }
        """
        contexts = self._extract_contexts()

        # Pre-pass: extract descriptions to avoid data loss and provide context
        descriptions_by_context: Dict[str, Dict[str, str]] = {}
        for elem in self.root.iter():
            if "contextRef" not in elem.attrib:
                continue

            tag = elem.tag.split("}")[-1]
            if tag.startswith("DescriptionOf") and elem.text:
                context_id = elem.attrib["contextRef"]
                base_tag = tag[len("DescriptionOf") :]

                if context_id not in descriptions_by_context:
                    descriptions_by_context[context_id] = {}
                descriptions_by_context[context_id][base_tag] = elem.text.strip()

        # Initialize result structure
        result: Dict[str, Dict[str, Any]] = {}

        for elem in self.root.iter():
            if "contextRef" not in elem.attrib:
                continue

            # Strip the namespace from the tag
            tag = elem.tag.split("}")[-1]
            context_id = elem.attrib["contextRef"]
            value = elem.text

            # Ignore tags without text values (e.g. containers)
            if value is None:
                continue

            value = value.strip()
            if not value:
                continue

            # Skip description tags as standalone metrics if they are used as modifiers
            if tag.startswith("DescriptionOf"):
                base_tag = tag[len("DescriptionOf") :]
                if context_id in descriptions_by_context and base_tag in descriptions_by_context[context_id]:
                    continue

            # Try to cast to number
            try:
                if "." in value or "e" in value.lower():
                    parsed_value = float(value)
                else:
                    parsed_value = int(value)
            except ValueError:
                parsed_value = value

            context_info = contexts.get(context_id)
            if not context_info:
                continue

            period_str = context_info["period_str"]
            dimensions = context_info.get("dimensions", {})
            desc_value = descriptions_by_context.get(context_id, {}).get(tag)

            # Append dimension string to the key to prevent overwriting
            metric_key = tag
            if dimensions or desc_value:
                modifiers = []
                if desc_value:
                    modifiers.append(f"Description='{desc_value}'")
                for k, v in sorted(dimensions.items()):
                    modifiers.append(f"{k}={v}")

                modifier_str = ",".join(modifiers)
                metric_key = f"{tag} [{modifier_str}]"

            if period_str not in result:
                result[period_str] = {}

            result[period_str][metric_key] = parsed_value

        return result
