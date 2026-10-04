# Before and after

Twenty short pairs showing what the `readable-code` skill changes and, in the last four, what it deliberately leaves alone. Each is labeled with the catalog rule IDs it demonstrates, so you can look the rule up in [`catalog/rules.yaml`](../catalog/rules.yaml) or the skill's [catalog table](../skills/readable-code/SKILL.md).

Every example here was written for this repository. None is adapted from *The Art of Readable Code*, and most use a different language and domain from any example the book uses for the same idea. The point of the last four is that over-application is the failure mode that costs the most trust, so restraint gets examples of its own.

| #   | Example                                                                                                     | Language   | Rules                 |
| --- | ----------------------------------------------------------------------------------------------------------- | ---------- | --------------------- |
| 1   | [Constants that hide their unit](#1-constants-that-hide-their-unit)                                         | Go         | `N3`                  |
| 2   | [Names that fit any function](#2-names-that-fit-any-function)                                               | TypeScript | `N1`, `N9`            |
| 3   | [A plan narrated in comments](#3-a-plan-narrated-in-comments)                                               | Python     | `X7`, `C1`, `C3`      |
| 4   | [A doc comment that restates the name](#4-a-doc-comment-that-restates-the-name)                             | Rust       | `C14`, `C15`          |
| 5   | [Nesting that only checks for null](#5-nesting-that-only-checks-for-null)                                   | C#         | `F6`                  |
| 6   | [A condition with a policy buried in it](#6-a-condition-with-a-policy-buried-in-it)                         | Kotlin     | `E1`, `E2`            |
| 7   | [Hand-rolled counting](#7-hand-rolled-counting)                                                             | Python     | `S8`, `V1`            |
| 8   | [An interface for one implementation](#8-an-interface-for-one-implementation)                               | TypeScript | `S6`                  |
| 9   | [Guards against states that cannot happen](#9-guards-against-states-that-cannot-happen)                     | Java       | `S7`                  |
| 10  | [Banners and emoji in a script](#10-banners-and-emoji-in-a-script)                                          | Bash       | `X8`, `C8`            |
| 11  | [Test names that say nothing](#11-test-names-that-say-nothing)                                              | Python     | `T3`                  |
| 12  | [A retry loop steered by a flag](#12-a-retry-loop-steered-by-a-flag)                                        | Go         | `V5`                  |
| 13  | [Negated and shapeless settings](#13-negated-and-shapeless-settings)                                        | TypeScript | `N10`, `N11`, `N16`   |
| 14  | [A range with unstated ends](#14-a-range-with-unstated-ends)                                                | Rust       | `N12`, `N13`, `N3`    |
| 15  | [Numbers with no reason attached](#15-numbers-with-no-reason-attached)                                      | C#         | `C5`, `C3`            |
| 16  | [A bugfix that grew a rewrite](#16-a-bugfix-that-grew-a-rewrite)                                            | Python     | `X1`, `X4`, `X3`      |
| 17  | [Restraint: a `tmp` that earns its name](#17-restraint-a-tmp-that-earns-its-name)                           | Go         | `N2`, `N5`            |
| 18  | [Restraint: a comment that only looks redundant](#18-restraint-a-comment-that-only-looks-redundant)         | Kotlin     | `C1`, `C7`            |
| 19  | [Restraint: a one-liner that stays inline](#19-restraint-a-one-liner-that-stays-inline)                     | TypeScript | `S6`, `V1`            |
| 20  | [Restraint: a public name you were not asked to fix](#20-restraint-a-public-name-you-were-not-asked-to-fix) | Ruby       | `X3`, `X2`, `X1`      |

## Applying a rule

Each pair below shows a small piece of code as an agent commonly writes it, then the same code after the skill's rules are applied, with a sentence or two on what changed for the reader.

### 1. Constants that hide their unit

Rules: `N3`. An IoT gateway that batches sensor readings.

```go
const (
    pollInterval = 30
    maxPayload   = 256
)

func (g *Gateway) Run(ctx context.Context) {
    for {
        g.upload(ctx, g.drain(maxPayload))
        time.Sleep(time.Duration(pollInterval) * time.Second)
    }
}
```

```go
const (
    pollInterval    = 30 * time.Second
    maxPayloadBytes = 256
)

func (g *Gateway) Run(ctx context.Context) {
    for {
        g.upload(ctx, g.drain(maxPayloadBytes))
        time.Sleep(pollInterval)
    }
}
```

`maxPayload` could be bytes or a count of readings, and the caller of `drain` had to guess. `pollInterval` needs no suffix once it is a `time.Duration`: where the language has a type that carries the unit, the type is the better fix.

### 2. Names that fit any function

Rules: `N1`, `N9`. A payment webhook consumer.

```ts
async function handleData(data: WebhookEvent[]): Promise<number> {
  let result = 0;
  for (const item of data) {
    if (item.type === "refund.created") {
      await ledger.reverse(item.chargeId);
      result++;
    }
  }
  return result;
}
```

```ts
async function reverseRefundedCharges(events: WebhookEvent[]): Promise<number> {
  let reversedCount = 0;
  for (const event of events) {
    if (event.type === "refund.created") {
      await ledger.reverse(event.chargeId);
      reversedCount++;
    }
  }
  return reversedCount;
}
```

Every name in the first version would fit any function in any codebase, so a caller seeing `const n = await handleData(batch)` learns nothing. The second version tells the call site what happens and what the returned number counts.

### 3. A plan narrated in comments

Rules: `X7`, `C1`, `C3`. A photo thumbnail step.

```python
def build_thumbnails(photo_paths, out_dir):
    # Step 1: Create the output directory
    out_dir.mkdir(parents=True, exist_ok=True)
    # Step 2: Loop through each photo
    for path in photo_paths:
        # Open the image
        with Image.open(path) as img:
            # Resize the image
            img.thumbnail((320, 320))
            # Save the thumbnail
            img.save(out_dir / path.name)
```

```python
def build_thumbnails(photo_paths, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in photo_paths:
        with Image.open(path) as img:
            # A bounding box, not the output size: thumbnail() keeps the aspect ratio.
            img.thumbnail((320, 320))
            img.save(out_dir / path.name)
```

The numbered steps were the author's plan, and every comment restated its line. The one comment left answers the question a reader would actually stop on: will a portrait photo come out as a 320-pixel square?

### 4. A doc comment that restates the name

Rules: `C14`, `C15`. A config-file duration parser.

```rust
/// Parses a duration.
pub fn parse_duration(text: &str) -> Option<Duration> {
    // ...
}
```

```rust
/// Parses a compact duration such as `"90s"`, `"15m"`, or `"1h30m"`.
///
/// Units are `h`, `m`, and `s`, largest first, each at most once.
/// Returns `None` for an empty string, an unknown unit, or a bare
/// number with no unit: `parse_duration("30")` is `None`, not 30 seconds.
pub fn parse_duration(text: &str) -> Option<Duration> {
    // ...
}
```

The caller's real questions are about the edges: is a bare number allowed, and which unit does it default to? The worked input answers the one most likely to cause a bug.

### 5. Nesting that only checks for null

Rules: `F6`. Looking up where an order ships.

```csharp
public string? ShippingCountryCode(Order order)
{
    if (order.Customer != null)
    {
        if (order.Customer.DefaultAddress != null)
        {
            if (!string.IsNullOrEmpty(order.Customer.DefaultAddress.CountryCode))
            {
                return order.Customer.DefaultAddress.CountryCode;
            }
        }
    }
    return null;
}
```

```csharp
public string? ShippingCountryCode(Order order)
{
    string? countryCode = order.Customer?.DefaultAddress?.CountryCode;
    return string.IsNullOrEmpty(countryCode) ? null : countryCode;
}
```

Three levels of nesting were asking one question: is anything along this path missing? The null-conditional operator asks it in a single expression, so the reader holds no conditions in mind. The flat version also makes visible a rule the nesting buried: an empty country code comes back as `null` too.

### 6. A condition with a policy buried in it

Rules: `E1`, `E2`. Airline change-fee waivers.

```kotlin
if (booking.fareClass in setOf(FareClass.FLEX, FareClass.BUSINESS) ||
    (passenger.loyaltyTier >= Tier.GOLD && booking.departure.minusHours(24).isAfter(now)) ||
    booking.wasRebookedByAirline
) {
    waiveChangeFee(booking)
}
```

```kotlin
val fareIncludesChanges = booking.fareClass in setOf(FareClass.FLEX, FareClass.BUSINESS)
val isMoreThanADayOut = booking.departure.minusHours(24).isAfter(now)
val goldMemberChangingEarly = passenger.loyaltyTier >= Tier.GOLD && isMoreThanADayOut

if (fareIncludesChanges || goldMemberChangingEarly || booking.wasRebookedByAirline) {
    waiveChangeFee(booking)
}
```

The first version is correct, but a reader has to decode it to learn the policy. In the second, the `if` reads as the policy: a flexible fare, an early gold-member change, or an airline rebooking each waives the fee.

### 7. Hand-rolled counting

Rules: `S8`, `V1`. Open support tickets per assignee, busiest first.

```python
def open_ticket_counts(tickets):
    counts = {}
    for ticket in tickets:
        if ticket.status == "open":
            if ticket.assignee in counts:
                counts[ticket.assignee] = counts[ticket.assignee] + 1
            else:
                counts[ticket.assignee] = 1
    sorted_counts = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)
    return sorted_counts
```

```python
from collections import Counter


def open_ticket_counts(tickets):
    open_assignees = (ticket.assignee for ticket in tickets if ticket.status == "open")
    return Counter(open_assignees).most_common()
```

`Counter.most_common()` is counting and ranking by name, already tested, and every Python reader knows it. Ties come out in the same first-seen order the stable `sorted` produced. `sorted_counts` went too, because it was assigned once, returned on the next line, and said nothing the expression did not.

### 8. An interface for one implementation

Rules: `S6`. A shipping-delay notice.

```ts
interface NotificationChannel {
  send(userId: string, message: string): Promise<void>;
}

class EmailChannel implements NotificationChannel {
  async send(userId: string, message: string): Promise<void> {
    await mailer.deliver(await lookupEmail(userId), message);
  }
}

function createChannel(kind: "email"): NotificationChannel {
  return new EmailChannel();
}

export async function notifyShipmentDelayed(userId: string, orderId: string) {
  const channel = createChannel("email");
  await channel.send(userId, `Order ${orderId} is running late.`);
}
```

```ts
export async function notifyShipmentDelayed(userId: string, orderId: string) {
  const address = await lookupEmail(userId);
  await mailer.deliver(address, `Order ${orderId} is running late.`);
}
```

One implementation, one caller, and a factory whose parameter accepts a single value. A reader stepped through three layers to find a `mailer.deliver` call. When a second channel really arrives, an interface shaped by two real cases will be a better one than this guess.

### 9. Guards against states that cannot happen

Rules: `S7`. A warehouse pick list. `Order` is a record whose constructor wraps its items in `List.copyOf`, which rejects both a null list and null elements.

```java
List<PickLine> buildPickList(Order order) {
    List<PickLine> lines = new ArrayList<>();
    if (order.items() == null) {
        return lines;
    }
    for (OrderItem item : order.items()) {
        if (item == null) {
            continue;
        }
        lines.add(new PickLine(item.sku(), item.quantity(), binFor(item.sku())));
    }
    return lines;
}
```

```java
List<PickLine> buildPickList(Order order) {
    List<PickLine> lines = new ArrayList<>();
    for (OrderItem item : order.items()) {
        lines.add(new PickLine(item.sku(), item.quantity(), binFor(item.sku())));
    }
    return lines;
}
```

A guard is a claim that its condition can occur. These two send a careful reader looking for the code path that produces a null item, and there isn't one. Removing them is safe only because the constructor makes the guarantee. Without that, they would stay.

### 10. Banners and emoji in a script

Rules: `X8`, `C8`. A release upload script.

```bash
#############################################
#           🚀 DEPLOY SCRIPT 🚀              #
#############################################

echo "✅ Building release..."
make release
echo "🎉 Uploading artifacts..."
rsync -a dist/ "$DEPLOY_HOST:/srv/app/releases/$VERSION/"
echo "✨ Done! ✨"
```

```bash
# Builds a release and copies it to $DEPLOY_HOST under releases/$VERSION.
# Does not switch the live symlink; promote.sh does that.

echo "Building release $VERSION"
make release
echo "Uploading to $DEPLOY_HOST"
rsync -a dist/ "$DEPLOY_HOST:/srv/app/releases/$VERSION/"
```

The banner took three lines to say the file's name. Those lines now answer the question that matters before running it: does this put the release live? The log lines also gained the values someone reading a failed CI log will want.

### 11. Test names that say nothing

Rules: `T3`. A URL slug generator.

```python
def test_slugify():
    assert slugify("Hello World") == "hello-world"


def test_slugify_2():
    assert slugify("  Café au lait!  ") == "cafe-au-lait"


def test_slugify_3():
    assert len(slugify("a" * 300)) <= 80
```

```python
def test_slugify_lowercases_and_hyphenates_words():
    assert slugify("Hello World") == "hello-world"


def test_slugify_drops_accents_punctuation_and_outer_spaces():
    assert slugify("  Café au lait!  ") == "cafe-au-lait"


def test_slugify_caps_long_input_at_80_chars():
    assert len(slugify("a" * 300)) <= 80
```

A test name is mostly read in a failure report, with the test body off screen. `test_slugify_3 FAILED` sends you to the file. `test_slugify_caps_long_input_at_80_chars FAILED` already tells you what broke.

### 12. A retry loop steered by a flag

Rules: `V5`. Dialing a service that may still be starting.

```go
func connectWithRetry(addr string, maxAttempts int) (net.Conn, error) {
    var conn net.Conn
    var lastErr error
    connected := false
    attempt := 0
    for !connected && attempt < maxAttempts {
        c, err := net.DialTimeout("tcp", addr, 2*time.Second)
        if err == nil {
            conn = c
            connected = true
        } else {
            lastErr = err
            attempt++
            time.Sleep(backoff(attempt))
        }
    }
    if !connected {
        return nil, fmt.Errorf("dial %s after %d attempts: %w", addr, maxAttempts, lastErr)
    }
    return conn, nil
}
```

```go
func connectWithRetry(addr string, maxAttempts int) (net.Conn, error) {
    var lastErr error
    for attempt := 1; attempt <= maxAttempts; attempt++ {
        conn, err := net.DialTimeout("tcp", addr, 2*time.Second)
        if err == nil {
            return conn, nil
        }
        lastErr = err
        time.Sleep(backoff(attempt))
    }
    return nil, fmt.Errorf("dial %s after %d attempts: %w", addr, maxAttempts, lastErr)
}
```

`connected` and the outer `conn` existed only to carry a success out of the loop so a later check could return it. Returning the moment the dial succeeds removes both, and the loop header now states the attempt count on its own instead of sharing it with the flag.

### 13. Negated and shapeless settings

Rules: `N10`, `N11`, `N16`. Editor settings in new code.

```ts
interface EditorSettings {
  noAutosave: boolean;
  spellcheck: boolean;
  lineWrap: number;
}

if (!settings.noAutosave && !isNotDirty(doc)) {
  scheduleSave(doc);
}
```

```ts
interface EditorSettings {
  autosaveEnabled: boolean;
  spellcheckEnabled: boolean;
  wrapColumn: number;
}

if (settings.autosaveEnabled && hasUnsavedChanges(doc)) {
  scheduleSave(doc);
}
```

`!settings.noAutosave && !isNotDirty(doc)` asks the reader to cancel four negations before they know when a save happens. `lineWrap` read as a boolean until its type said otherwise. This applies to code you are writing. Renaming fields on an interface other code already uses is a different decision ([example 20](#20-restraint-a-public-name-you-were-not-asked-to-fix)).

### 14. A range with unstated ends

Rules: `N12`, `N13`, `N3`. An HTTP `Range` header, whose byte ranges include both ends.

```rust
pub struct ByteRange {
    pub start: u64,
    pub end: u64,
}

fn parse_range_header(value: &str, limit: u64) -> Option<ByteRange> { /* ... */ }

let body_len = range.end - range.start;
```

```rust
/// Both ends inclusive, as in the header: `bytes=0-499` is the first 500 bytes.
pub struct ByteRange {
    pub first_byte: u64,
    pub last_byte: u64,
}

fn parse_range_header(value: &str, max_len_bytes: u64) -> Option<ByteRange> { /* ... */ }

let body_len = range.last_byte - range.first_byte + 1;
```

`start` and `end` usually mean the end is excluded, and the subtraction in the first version trusted that reading, so every response came out one byte short. `first_byte` and `last_byte` say both ends are in. `limit` became `max_len_bytes`, so the name says it is an upper bound and gives its unit.

### 15. Numbers with no reason attached

Rules: `C5`, `C3`. Batching outbound SMS through a third-party gateway.

```csharp
private const int MaxBatchSize = 40;
private static readonly TimeSpan RetryDelay = TimeSpan.FromSeconds(7);
```

```csharp
// The gateway documents a cap of 50 recipients per request, but under load it
// starts returning 429s above 40. Measured in the March incident review.
private const int MaxBatchSize = 40;

// Longer than the gateway's 5-second rate-limit window, so a retry never lands
// in the window that rejected it.
private static readonly TimeSpan RetryDelay = TimeSpan.FromSeconds(7);
```

Without the comments, the next person to read the vendor docs raises `MaxBatchSize` to 50, or rounds the delay to 5 seconds. Both values come from facts about the outside world that the code cannot show.

### 16. A bugfix that grew a rewrite

Rules: `X1`, `X4`, `X3`. The task was a bug report: loyalty points are multiplied twice.

The diff an agent produced:

```diff
-def calc_pts(order, member):
-    pts = int(order.total_cents / 100) * member.multiplier
-    pts = pts * member.multiplier
-    return pts
+def calculate_loyalty_points(order: Order, member: Member) -> int:
+    """Return the loyalty points earned for an order."""
+    whole_dollars = order.total_cents // 100
+    return whole_dollars * member.multiplier
```

The diff the task asked for:

```diff
 def calc_pts(order, member):
     pts = int(order.total_cents / 100) * member.multiplier
-    pts = pts * member.multiplier
     return pts
```

The first diff fixes the bug and also renames a function other modules import, which breaks them. Hidden inside the cleanup is a second behavior change: `int(x / 100)` rounds toward zero and `x // 100` rounds down, so a refund of `-150` cents now costs the member two points instead of one. A reviewer looking for the one-line fix would not see that. The narrow fix ships alone, and the rename goes into the report as a suggested follow-up.

## When not to apply a rule

Over-application is the failure mode that costs the most trust, because a reader who has to review renames and deletions they did not ask for stops trusting the rest of the diff. Each example below shows code that is fine as written, the change a rule seems to call for, and why the rule does not apply.

### 17. Restraint: a `tmp` that earns its name

Rules: `N2`, `N5`. Writing a config file atomically.

```go
func writeConfigAtomically(path string, contents []byte) error {
    tmp := path + ".tmp"
    if err := os.WriteFile(tmp, contents, 0o600); err != nil {
        return err
    }
    return os.Rename(tmp, path)
}
```

The tempting change renames `tmp` to something like `stagingFilePathForAtomicRename`, on the grounds that `tmp` is a placeholder name.

Leave it. This file really is temporary, the variable lives for four lines that fit in one glance, and the function name already says why it exists. A longer name here costs reading time on every line that uses it and says nothing new.

### 18. Restraint: a comment that only looks redundant

Rules: `C1`, `C7`. A job scheduler's run queue.

```kotlin
// Stable sort: jobs with equal priority keep their submission order.
val queue = pending.sortedBy { it.priority }
```

The tempting change deletes the comment for restating the code, since the line plainly sorts by priority.

Leave it. The line shows *that* it sorts. The comment records that the code depends on the sort being stable, which nothing on the line shows. Someone swapping in a faster unstable sort, or a parallel one, would quietly break first-come-first-served among equal priorities, and this comment is the only thing standing in their way.

### 19. Restraint: a one-liner that stays inline

Rules: `S6`, `V1`. Sending invoice reminders.

```ts
const overdue = invoices.filter((invoice) => invoice.dueDate < today);
await sendReminders(overdue);
```

Two changes are tempting, in opposite directions. One extracts a `getOverdueInvoices(invoices, today)` helper "for reuse". The other inlines `overdue` because it is used once, on the very next line.

Leave both alone. The helper would have one caller and a name that says no more than the `filter` it wraps, so a reader would have to jump to it to learn nothing. The variable stays because its name says something the expression doesn't: `overdue` reads faster than the predicate. A name used once is worth removing only when it says no more than what it holds.

### 20. Restraint: a public name you were not asked to fix

Rules: `X3`, `X2`, `X1`. The task was to add a tax rate to an existing billing module.

```ruby
module Billing
  # Called by the mobile sync endpoint and two partner integrations.
  def self.calc_amt(line_items, tax_rate: 0)
    subtotal = line_items.sum { |li| li.unit_price_cents * li.qty }
    (subtotal * (1 + tax_rate)).round
  end
end
```

The tempting change renames `calc_amt` to `calculate_total_cents`, and `li` and `qty` to full words, while the file is open anyway.

Leave the names. `calc_amt` is called from outside this repository, so renaming it breaks callers that no test here will catch. `li` and `qty` match the vocabulary the rest of the module uses. A rename was not the task. The right move is the `tax_rate` change above, plus one line in the report: "`calc_amt` doesn't say what it returns. Consider renaming it in a separate change that updates the partner integrations."
