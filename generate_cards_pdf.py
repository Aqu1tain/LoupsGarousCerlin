#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Werewolf card game PDF generator.
Generates print-ready PDFs with optimal card layout and cutting instructions.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from collections import defaultdict
from enum import Enum

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm


# Constants
CARDS_DIR = Path("Cartes")
OUTPUT_FILENAME = "cartes_impression.pdf"

# Layout constants (in mm)
MARGIN = 15
CARD_MAX_SIZE = 80
CARD_SPACING_V = 8
CARD_SPACING_H_MIN = 10

# Card types and filenames
class CardType(Enum):
    VILLAGER = "Simple Villageois.png"
    WEREWOLF = "Loup Garou.png"
    FEATHERS = "Plumes du corbeau.png"
    CAPTAIN = "Capitaine.png"
    BACK = "Dos-Cartes.png"


# Card multipliers for game balance
CARD_QUANTITIES = {
    CardType.VILLAGER: 6,
    CardType.WEREWOLF: 4,
    CardType.FEATHERS: 2,
    CardType.CAPTAIN: 2,
}

# Mapping for quantity keys (French naming consistency)
QUANTITY_KEYS = {
    CardType.VILLAGER: 'villageois_count',
    CardType.WEREWOLF: 'loup_garou_count',
    CardType.FEATHERS: 'plumes_corbeau_count',
    CardType.CAPTAIN: 'capitaine_count',
}

# Mapping for presence flags (French naming consistency)
PRESENCE_FLAGS = {
    CardType.VILLAGER: 'has_villageois',
    CardType.WEREWOLF: 'has_loup_garou',
    CardType.FEATHERS: 'has_plumes_corbeau',
    CardType.CAPTAIN: 'has_capitaine',
    CardType.BACK: 'has_dos',
}

# Cards that get glued back-to-back (reduces back card count)
DOUBLE_SIDED_CARDS = {CardType.VILLAGER, CardType.CAPTAIN, CardType.FEATHERS}


@dataclass
class CardInventory:
    """Represents the card inventory and calculated quantities."""
    categorized: Dict[CardType, List[Path]]
    others: List[Path]
    quantities: Dict[str, int]

    @property
    def total_face_cards(self) -> int:
        return self.quantities['total_cartes_face']

    @property
    def back_count(self) -> int:
        return self.quantities['dos_count']

    @property
    def total_cards(self) -> int:
        return self.quantities['total_cartes']


class LayoutConfig(NamedTuple):
    """PDF layout configuration."""
    card_size: float
    cards_per_row: int
    cards_per_col: int
    horizontal_spacing: float

    @property
    def cards_per_page(self) -> int:
        return self.cards_per_row * self.cards_per_col


class CardPDFGenerator:
    """Handles PDF generation for werewolf card game."""

    def __init__(self, output_filename: str = OUTPUT_FILENAME):
        self.output_filename = output_filename
        self.page_width, self.page_height = A4

    def generate(self, inventory: CardInventory) -> None:
        """Generate the complete PDF with instructions and cards."""
        cards_to_print = self._prepare_card_list(inventory)
        layout = self._calculate_layout()

        print(f"Generating {len(cards_to_print)} cards ({layout.card_size/mm:.0f}x{layout.card_size/mm:.0f}mm)")
        print(f"Layout: {layout.cards_per_row} cards/row, {layout.cards_per_col} rows/page")

        c = canvas.Canvas(self.output_filename, pagesize=A4)

        # Add instructions page
        self._add_instructions_page(c, inventory)
        c.showPage()

        # Add card pages
        self._add_card_pages(c, cards_to_print, layout)

        c.save()
        print(f"\n✅ PDF generated: {self.output_filename}")

    def _prepare_card_list(self, inventory: CardInventory) -> List[Path]:
        """Build the final list of cards to print based on calculated quantities."""
        cards = []

        # Add quantity-based cards
        for card_type in [CardType.VILLAGER, CardType.WEREWOLF, CardType.FEATHERS, CardType.CAPTAIN]:
            quantity_key = QUANTITY_KEYS.get(card_type)
            if quantity_key and card_type in inventory.categorized and inventory.quantities[quantity_key] > 0:
                cards.extend(
                    inventory.categorized[card_type][0]
                    for _ in range(inventory.quantities[quantity_key])
                )

        # Add other unique cards
        cards.extend(inventory.others)

        # Add card backs
        if CardType.BACK in inventory.categorized and inventory.back_count > 0:
            cards.extend(
                inventory.categorized[CardType.BACK][0]
                for _ in range(inventory.back_count)
            )

        return cards

    def _calculate_layout(self) -> LayoutConfig:
        """Calculate optimal card layout for A4 page."""
        available_width = self.page_width - 2 * MARGIN * mm
        available_height = self.page_height - 2 * MARGIN * mm

        # Square cards, 2 per row
        cards_per_row = 2
        card_size = min(CARD_MAX_SIZE * mm, (available_width - CARD_SPACING_H_MIN * mm) / 2)

        total_card_width = cards_per_row * card_size
        horizontal_spacing = (available_width - total_card_width) / (cards_per_row + 1)

        cards_per_col = int(available_height // (card_size + CARD_SPACING_V * mm))

        return LayoutConfig(card_size, cards_per_row, cards_per_col, horizontal_spacing)

    def _add_instructions_page(self, c: canvas.Canvas, inventory: CardInventory) -> None:
        """Add instructions page with dynamic content based on inventory."""
        margin_left = 20 * mm
        margin_right = 20 * mm
        y_pos = self.page_height - 35 * mm

        # Title
        c.setFont("Helvetica-Bold", 20)
        c.drawString(margin_left, y_pos, "🐺 Loup-Garou de Crénin")

        y_pos -= 10 * mm
        c.setFont("Helvetica", 16)
        c.drawString(margin_left, y_pos, "Guide d'impression")

        # Sections with their content
        sections = [
            ("📋 Découpe", [
                "• Papier épais (200-300g/m²), découpe carré 1:1, cutter + règle",
                "• Arrondissez les coins avec des ciseaux"
            ]),
            ("🔗 Assemblage dos-à-dos", [
                "• 2 Capitaines → 1 carte collée dos-à-dos",
                "• 2 Plumes du corbeau → 1 carte collée dos-à-dos",
                "• 2 Villageois → 1 carte 'Villageois-Villageois'",
                "• Loups garous : cartes individuelles (pas de collage)"
            ]),
            ("✨ Finition", [
                "• RECOMMANDÉ : Plastification 80-125 microns",
                "• 2-3mm marge avant plastification, 1mm après découpe finale"
            ])
        ]

        y_pos -= 20 * mm
        for title, items in sections:
            c.setFont("Helvetica-Bold", 14)
            c.drawString(margin_left, y_pos, title)

            y_pos -= 8 * mm
            c.setFont("Helvetica", 11)
            for item in items:
                c.drawString(margin_left + 5 * mm, y_pos, item)
                y_pos -= 5 * mm
            y_pos -= 5 * mm

        # Dynamic game content
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin_left, y_pos, "🎲 Contenu")

        y_pos -= 8 * mm
        c.setFont("Helvetica", 11)

        content_items = self._generate_content_summary(inventory)
        for item in content_items:
            if item:
                c.drawString(margin_left + 5 * mm, y_pos, item)
            y_pos -= 5 * mm

        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(margin_left, 25 * mm, "Loup-Garou de Crénin - Open source sur GitHub")
        c.drawString(margin_left, 15 * mm, "Bon jeu ! 🌙")

    def _generate_content_summary(self, inventory: CardInventory) -> List[str]:
        """Generate dynamic content summary for instructions page."""
        items = []

        type_to_desc = {
            CardType.VILLAGER: "Villageois → 3x Villageois-Villageois",
            CardType.WEREWOLF: "Loup Garou (séparés)",
            CardType.FEATHERS: "Plumes → 1x collée",
            CardType.CAPTAIN: "Capitaine → 1x collée",
        }

        for card_type, desc in type_to_desc.items():
            qty_key = QUANTITY_KEYS.get(card_type)
            if qty_key and card_type in inventory.categorized and inventory.quantities[qty_key] > 0:
                items.append(f"• {inventory.quantities[qty_key]}x {desc}")

        if inventory.quantities['autres_cartes'] > 0:
            items.append(f"• {inventory.quantities['autres_cartes']}x Cartes spéciales")

        if CardType.BACK in inventory.categorized:
            items.append(f"• {inventory.back_count}x Dos")

        items.extend(["", f"Total final : {inventory.total_face_cards - 3} cartes physiques"])

        return items

    def _add_card_pages(self, c: canvas.Canvas, cards: List[Path], layout: LayoutConfig) -> None:
        """Add all card pages to the PDF."""
        total_pages = (len(cards) + layout.cards_per_page - 1) // layout.cards_per_page

        for page_num in range(total_pages):
            if page_num > 0:
                c.showPage()

            start_idx = page_num * layout.cards_per_page
            end_idx = min(start_idx + layout.cards_per_page, len(cards))

            print(f"Page {page_num + 2}: cards {start_idx + 1} to {end_idx}")

            for i in range(start_idx, end_idx):
                self._draw_card(c, cards[i], i - start_idx, layout)

    def _draw_card(self, c: canvas.Canvas, card_path: Path, position: int, layout: LayoutConfig) -> None:
        """Draw a single card at the specified position."""
        row = position // layout.cards_per_row
        col = position % layout.cards_per_row

        x = MARGIN * mm + layout.horizontal_spacing + col * (layout.card_size + layout.horizontal_spacing)
        y = self.page_height - MARGIN * mm - layout.card_size - row * (layout.card_size + CARD_SPACING_V * mm)

        try:
            c.drawImage(str(card_path), x, y, width=layout.card_size, height=layout.card_size)
        except Exception as e:
            print(f"Error drawing card {card_path}: {e}")
            # Fallback: draw placeholder
            c.rect(x, y, layout.card_size, layout.card_size)
            c.drawString(x + 5, y + layout.card_size/2, f"Error: {card_path.name}")


def scan_card_files() -> List[Path]:
    """Scan for PNG files in the cards directory."""
    if not CARDS_DIR.exists():
        raise FileNotFoundError(f"Cards directory '{CARDS_DIR}' not found")

    return list(CARDS_DIR.glob("*.png"))


def categorize_cards(card_files: List[Path]) -> CardInventory:
    """Categorize cards and calculate quantities based on game rules."""
    categorized = defaultdict(list)
    others = []

    # Categorize by type
    type_mapping = {card_type.value: card_type for card_type in CardType}

    for card_path in card_files:
        filename = card_path.name
        if filename in type_mapping:
            categorized[type_mapping[filename]].append(card_path)
        else:
            others.append(card_path)

    # Calculate quantities
    quantities = _calculate_quantities(categorized, others)

    return CardInventory(dict(categorized), others, quantities)


def _calculate_quantities(categorized: Dict[CardType, List[Path]], others: List[Path]) -> Dict[str, int]:
    """Calculate dynamic card quantities based on available files."""
    quantities = {}

    # Base quantities from constants
    for card_type, base_qty in CARD_QUANTITIES.items():
        key = QUANTITY_KEYS[card_type]
        quantities[key] = base_qty if card_type in categorized else 0

    # Other cards count
    quantities['autres_cartes'] = len(others)

    # Total face cards
    total_face = (
        len(others) +
        sum(quantities.get(key, 0) for key in QUANTITY_KEYS.values())
    )
    quantities['total_cartes_face'] = total_face

    # Back cards calculation (accounting for double-sided cards)
    double_sided_reduction = sum(
        2 for card_type in DOUBLE_SIDED_CARDS
        if card_type in categorized
    )
    quantities['dos_count'] = max(0, total_face - 6) if CardType.BACK in categorized else 0

    # Total cards
    quantities['total_cartes'] = total_face + quantities['dos_count']

    # Presence flags for instructions
    for card_type, flag_key in PRESENCE_FLAGS.items():
        quantities[flag_key] = card_type in categorized

    return quantities


def main():
    """Main entry point."""
    print("=== Werewolf Card PDF Generator ===\n")

    try:
        # Scan for card files
        card_files = scan_card_files()
        print(f"Found {len(card_files)} card files")

        # Categorize and calculate quantities
        inventory = categorize_cards(card_files)

        # Display analysis
        print(f"\nDynamic analysis:")
        print(f"  Face cards: {inventory.total_face_cards}")
        print(f"  Back cards: {inventory.back_count}")
        print(f"  Total: {inventory.total_cards}")

        # Generate PDF
        generator = CardPDFGenerator()
        generator.generate(inventory)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())