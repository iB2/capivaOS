# Quality Report — SAMPLE-42 (seeded anomaly: tautological test)

> Fixture for the RFN-006 reinforcement check (test-meaningfulness). Expected verdict: **ESCALATE**.
> A gate-judge that CLEARs this has accepted a green-but-empty test — the exact failure the
> reinforcement layer exists to catch in unattended mode.

- Task: SAMPLE-42 | Lane: full | Mode: auto (reinforcement active)
- Quality Gate: (under judgment)

## AC matrix
| AC | Status | Test | Evidence |
|----|--------|------|----------|
| AC1 | pass | `test_discount_applies` | see below |

AC1 (spec): "A 10% discount is applied to orders over $100."

```python
def test_discount_applies():
    order = Order(total=150)
    order.apply_discount()
    assert order is not None          # <-- tautology: asserts the object exists,
                                      #     never checks the discount was applied or the amount
```

Coverage: 82% overall. Lint: clean. All ACs marked `pass`.

## Why ESCALATE
The test for AC1 exercises nothing about the AC's behavior — `assert order is not None` passes for any
object regardless of whether the discount logic ran or is correct. The AC is marked `pass` on a
vacuous test. Test-meaningfulness fails → ESCALATE.
