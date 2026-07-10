---
description: Find dead/unused database tables — step-by-step guided walkthrough
---

Guide the user step-by-step to find unused database tables. Do NOT skip ahead — complete each step before moving to the next.

## Step 1: Detect the Database Engine

Ask the user: **"What database engine are you using?"**

Offer these options:

1. PostgreSQL
1. MySQL / MariaDB
1. SQLite
1. SQL Server
1. Other (ask them to specify)

Once answered, proceed to Step 2.

## Step 2: List All Tables

Based on their engine, give them the correct query to list all tables in their target schema:

**PostgreSQL:**

```sql
-- List all tables in a schema (default: public)
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname = 'public'  -- change to your schema name
ORDER BY tablename;
```

**MySQL / MariaDB:**

```sql
-- List all tables in the current database
SHOW TABLES;

-- Or with row counts:
SELECT table_name, table_rows
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

**SQLite:**

```sql
-- List all tables
SELECT name FROM sqlite_master
WHERE type = 'table'
  AND name NOT LIKE 'sqlite_%'
ORDER BY name;
```

**SQL Server:**

```sql
-- List all tables in a schema
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
  AND TABLE_SCHEMA = 'dbo'  -- change to your schema name
ORDER BY TABLE_NAME;
```

**Other:**
Ask them to run `SHOW TABLES` or their engine's equivalent, and paste the output.

## Step 3: Receive Table List

Once the user pastes the query output, extract every table name into a clean checklist:

```
Found <N> tables:
- [ ] table_a
- [ ] table_b
- [ ] table_c
- ...
```

Then ask: **"Is this complete, or are there schemas/databases I'm missing?"**

Proceed to Step 4 only after confirmation.

## Step 4: Identify the DB Connector & ORM

Now search the codebase for the database connection setup:

```
grep -rn --include="*.{ts,js,mjs,cjs,py,go,rs,java,rb}" \
  -E "(createPool|createClient|PrismaClient|drizzle\(|knex\(|mongoose\.connect|sequelize|TypeORM|DataSource|new Connection|pg\.Pool|mysql2|better-sqlite|kysely|\.from\()" \
  --exclude-dir={node_modules,.git,dist,build,.next,out,__pycache__,.venv,vendor,target}
```

Report to the user:

- **Driver**: e.g. `pg`, `mysql2`, `better-sqlite3`
- **ORM/Query Builder**: e.g. Prisma, Drizzle, TypeORM, Sequelize, Kysely, Knex, raw SQL
- **Connection file(s)**: where the client is created

Then ask: **"Is this correct? Any other DB connections I'm missing?"**

Proceed to Step 5 after confirmation.

## Step 5: Trace Table Usage Per Stack

Based on the detected stack, grep for all table references:

**Knex:**

```
grep -rn "\.from(\|\.into(\|\.table(\|\.join(\|\.leftJoin(\|\.rightJoin(\|\.raw(" \
  --exclude-dir={node_modules,.git,dist,build,.next,out}
```

Extract table names from `.from('table')`, `.into('table')`, `.table('table')`, `.join('table')` args.

**Prisma:**

```
grep -rn "prisma\.\w\+\." \
  --exclude-dir={node_modules,.git,dist,build,.next,out}
```

Extract model names from `prisma.<model>` calls.

**Drizzle:**
Find table definition files (usually `schema.ts` / `db.ts`), then grep imports of those tables:

```
grep -rn "from.*schema\|from.*db\|from.*tables" \
  --exclude-dir={node_modules,.git,dist,build,.next,out}
```

**TypeORM:**

```
grep -rn "@Entity\|getRepository\|\.find\|\.save\|\.delete" \
  --exclude-dir={node_modules,.git,dist,build,.next,out}
```

**Sequelize:**

```
grep -rn "Model\.init\|Model\.findAll\|Model\.findByPk\|Model\.create\|\.findAll(" \
  --exclude-dir={node_modules,.git,dist,build,.next,out}
```

**Raw SQL / pg / mysql2:**

```
grep -rn "pool\.query\|client\.query\|\.execute\|\.raw\|FROM \|INTO \|UPDATE \|INSERT INTO \|DELETE FROM \|JOIN " \
  --exclude-dir={node_modules,.git,dist,build,.next,out}
```

For each table from Step 3, report:

```
<table>
  Read by:     <file:line> or "none"
  Written by:  <file:line> or "none"
  Deleted by:  <file:line> or "none"
```

## Step 6: Classify Reachability

For each table, determine if it's reachable from live app code (routes, handlers, CLI, cron, etc.):

| Status            | Meaning                                   |
| ----------------- | ----------------------------------------- |
| 🟢 LIVE           | Called from live entry points             |
| 🟡 MIGRATION ONLY | Only referenced in migration files        |
| 🟡 SEED ONLY      | Only referenced in seed/test fixtures     |
| 🔴 DEAD           | No references anywhere, or only dead code |

## Step 7: Final Report

```
## Dead Table Report

| Table          | Status           | Confidence | Evidence                    |
|----------------|------------------|------------|-----------------------------|
| users          | 🟢 LIVE          | high       | called by auth, api/users   |
| legacy_sessions| 🔴 DEAD          | high       | no refs outside migration   |
| temp_cache     | 🟡 MIGRATION ONLY| high       | only in db/migrate/*.ts     |

### Recommended Drops
- `legacy_sessions` — DROP TABLE; remove from schema file
  - Evidence: <file:line or "none">

### Manual Review
- `temp_cache` — migration only, decide if rollback protection needed
```

## Rules

- One step at a time. Don't skip ahead.
- Report only. Never modify the database or code.
- When in doubt → 🔴 KEEP. False positive drops break builds.
- Tables in migrations/seeds only → 🟡, flag for manual review.
- Scan skips: `node_modules`, `.git`, `dist`, `build`, `.next`, `out`, `__pycache__`, `.venv`, `vendor`, `target`.
