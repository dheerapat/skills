---
name: solid
description: Implement code using SOLID principles with concrete Python do/don't examples per rule. Use when user asks for solid design, refactoring, or clean architecture.
---

# solid

Code must follow SOLID. Each rule below is specific with Python `DO` and `DON'T`. No vague advice.

---

## S — Single Responsibility

A class has one reason to change. One job, not a bag of helpers.

DO:
```python
class InvoicePrinter:
    def print(self, invoice: Invoice) -> str:
        return f"Total: {invoice.total}"
```

DON'T:
```python
class InvoicePrinterAndSaver:  # mixes print + persistence
    def print(self, invoice): ...
    def save_to_db(self, invoice): ...
```

---

## O — Open/Closed

Open for extension via new subclasses / strategy objects. Closed for modification of existing working code.

DO:
```python
class ReportExporter:
    def export(self, data) -> bytes: ...

class CsvExporter(ReportExporter):
    def export(self, data): return data.to_csv()
```

DON'T:
```python
def export(data, format="csv"):
    if format == "csv": ...
    elif format == "pdf": ...  # modify this function for every new format
```

---

## L — Liskov Substitution

Subtypes must be fully substitutable for their base type without altering program correctness.

DO:
```python
class Bird:
    def fly(self): pass

class Sparrow(Bird):
    def fly(self): ...  # Sparrow can fly — substitutable
```

DON'T:
```python
class Penguin(Bird):
    def fly(self): raise NotImplementedError  # breaks substitution
```
Fix: split `FlyingBird` from `Bird`.

---

## I — Interface Segregation

Clients depend only on interfaces they use. No fat interfaces.

DO:
```python
class Printable:
    def print(self): ...

class Scannable:
    def scan(self): ...

class MultiFunctionPrinter(Printable, Scannable): ...
```

DON'T:
```python
class Machine:
    def print(self): ...
    def scan(self): ...
    def fax(self): ...  # clients forced to know fax even if they only print
```

---

## D — Dependency Inversion

Depend on abstractions (protocols / abstract base classes), not concrete implementations.

DO:
```python
from typing import Protocol

class NotificationService(Protocol):
    def send(self, msg: str) -> None: ...

class EmailService:
    def send(self, msg): ...

class Alert:
    def __init__(self, svc: NotificationService):  # abstract dependency
        self.svc = svc
```

DON'T:
```python
class Alert:
    def __init__(self):
        self.svc = EmailService()  # hardwired concrete — can't swap for SMS
```

---

## Quick Check

Before committing: does any class change for >1 reason (S)? Does adding a feature require editing existing files (O)? Can all subclasses replace parents safely (L)? Are interfaces split by use (I)? Are dependencies injected as abstractions (D)?
