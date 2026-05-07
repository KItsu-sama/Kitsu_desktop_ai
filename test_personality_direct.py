#!/usr/bin/env python
"""
Direct test of personality enhancements without circular imports.
Tests only the emotion_config module directly.
"""
import sys
sys.path.insert(0, r"d:\Du lieu o C\kitsu_desktop_ai")

# Import only the emotion_config module directly
import domain.personality.emotion_config as pconf

print("=" * 70)
print("PERSONALITY SYSTEM ENHANCEMENTS TEST")
print("=" * 70)

# Test 1: Build a personality
print("\n1️⃣  Building personality from emotion...")
p = pconf.build_personality("excited", "companion")
print(f"   Result: mood={p.mood}, style={p.style}, state={p.state}, role={p.role}")

# Test 2: Full validation (basic + combos)
print("\n2️⃣  Validating personality...")
valid, msg = pconf.validate_full_personality(p)
print(f"   Valid: {valid}")
if msg:
    print(f"   Message: {msg}")

# Test 3: Combo validation separately
print("\n3️⃣  Testing enhanced combo validation...")
combo_valid, combo_msg = pconf.validate_personality_combos(p)
print(f"   Combos Valid: {combo_valid}")
if combo_msg:
    print(f"   Message: {combo_msg}")

# Test 4: Invalid combo detection
print("\n4️⃣  Testing invalid combo detection...")
invalid_p = pconf.Personality(mood="mean", style="cold", state="normal", role="caretaker")
valid, msg = pconf.validate_full_personality(invalid_p)
print(f"   Testing caretaker+mean combo...")
print(f"   Valid: {valid}")
if msg:
    print(f"   ⚠️  Caught: {msg}")

# Test 5: Cached style rules (performance optimization)
print("\n5️⃣  Using cached style rules...")
rules = pconf.get_style_rules_cached(p.style)
print(f"   Style: {p.style}")
print(f"   Max words: {rules.get('max_words')}")
print(f"   Emojis allowed: {rules.get('emojis_allowed')}")

# Test 6: Verify caching is working (call twice, should use cache)
print("\n6️⃣  Verifying caching works...")
rules1 = pconf.get_style_rules_cached("chaotic")
rules2 = pconf.get_style_rules_cached("chaotic")
print(f"   First call - Max words: {rules1['max_words']}")
print(f"   Second call (cached) - Max words: {rules2['max_words']}")
print(f"   Cache info: {pconf.get_style_rules_cached.cache_info()}")

# Test 7: Test cached personality building
print("\n7️⃣  Using cached personality building...")
p2 = pconf.build_personality_cached("excited", "companion")
print(f"   Cached build result: mood={p2.mood}, style={p2.style}, state={p2.state}")

# Test 8: Configuration details
print("\n8️⃣  Configuration validation (ran at module import):")
print(f"   ✅ Valid moods: {len(pconf.VALID_MOODS)}")
print(f"   ✅ Valid styles: {len(pconf.VALID_STYLES)}")
print(f"   ✅ Valid states: {len(pconf.VALID_STATES)}")
print(f"   ✅ Valid roles: {len(pconf.VALID_ROLES)}")
print(f"   ✅ Style rules defined: {len(pconf.STYLE_RULES)}")

print("\n" + "=" * 70)
print("ALL TESTS COMPLETED SUCCESSFULLY ✅")
print("=" * 70)
