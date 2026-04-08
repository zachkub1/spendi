/**
 * Card image utilities.
 *
 * Images live in `public/cards/` and are served at `/cards/{slug}.png`.
 * The slug is derived from the card's display name so that any card —
 * whether chosen from the popular-cards grid or typed in manually — will
 * automatically pick up its artwork as soon as the corresponding file is
 * dropped into public/cards/.
 *
 * Naming convention for image files:
 *   "Chase Sapphire Preferred"      → /cards/chase-sapphire-preferred.png
 *   "American Express Gold Card"    → /cards/american-express-gold-card.png
 *   "Citi Double Cash Card"         → /cards/citi-double-cash-card.png
 *
 * Supported extension order (first match wins): .png, .jpg, .webp
 * In practice, just drop a .png and it will resolve automatically because
 * the <img onError> fallback is handled in the component.
 */

/** Convert a card display name into a URL-safe slug. */
export function cardNameToSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

/**
 * Return the public path for a card image given its display name.
 * The caller is responsible for handling the case where the image
 * doesn't exist (use onError → show placeholder).
 */
export function cardImagePath(displayName: string): string {
  return `/cards/${cardNameToSlug(displayName)}.png`;
}

/**
 * Explicit slug catalogue for the 9 popular cards.
 * This doubles as documentation for the expected filenames.
 *
 * Drop the matching .png into frontend/public/cards/ to activate artwork:
 *
 *   chase-sapphire-preferred.png
 *   chase-sapphire-reserve.png
 *   discover-it-student.png
 *   capital-one-venture-rewards.png
 *   american-express-gold-card.png
 *   american-express-platinum-card.png
 *   citi-double-cash-card.png
 *   wells-fargo-active-cash-card.png
 *   capital-one-quicksilver.png
 */
export const POPULAR_CARD_SLUGS: Record<string, string> = {
  "Chase Sapphire Preferred":      "chase-sapphire-preferred",
  "Chase Sapphire Reserve":        "chase-sapphire-reserve",
  "Discover it Student":           "discover-it-student",
  "Capital One Venture Rewards":   "capital-one-venture-rewards",
  "American Express Gold Card":    "american-express-gold-card",
  "American Express Platinum Card":"american-express-platinum-card",
  "Citi Double Cash Card":         "citi-double-cash-card",
  "Wells Fargo Active Cash Card":  "wells-fargo-active-cash-card",
  "Capital One Quicksilver":       "capital-one-quicksilver",
};
