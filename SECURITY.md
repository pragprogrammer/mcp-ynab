# Security

This document describes what this server protects, what it deliberately does not,
and how to operate it safely. Where a protection has a limit, the limit is stated
here rather than left for you to discover.

## Threat model

### What was actually wrong

The model never had access to your YNAB token. This server runs as a local
subprocess; the LLM only ever sees tool *return values*, never process memory and
never the environment block.

The real leak was mundane. A setup line like:

```bash
claude mcp add-json ynab --scope user '{...,"env":{"YNAB_API_KEY":"..."}}'
```

writes the token **in plaintext into the MCP client's own config file** —
`~/.claude.json`, `claude_desktop_config.json`, or a project `.env.local`. Any
agent with a file-read or shell tool, which is most of them including Claude Code
itself, can open that file and read the token. It also lands in shell history.

That is the hole this closes.

### What the fix achieves

The token lives in the OS credential store (Windows Credential Manager, macOS
Keychain, Secret Service on Linux) under the service name `mcp-ynab`. It is:

- out of every config file an agent can read,
- out of the process environment block,
- out of shell history — `mcp-ynab auth login` reads it with `getpass`, never
  from `argv`,
- a `SecretStr` in the process, unwrapped at exactly one line (the `Authorization`
  header in `YNABClient.__init__`) and never stored on the client afterwards,
- scrubbed out of every error string a tool returns, as a backstop for YNAB error
  bodies and `httpx` exception reprs that can echo request headers.

That is meaningful and worth doing.

### What the fix does not achieve

**DPAPI, Keychain and Secret Service scope secrets to the logged-in *user*, not
to a particular *program*.** Code running as the same user can ask the credential
store for the same secret and get it. An agent with shell access as that user can
still retrieve your YNAB token.

Closing that gap requires a separate OS account, a hardware token, or a broker
process that authenticates its callers — none of which a pip-installable MCP
server can deliver. Do not read anything in this document as a claim otherwise.

What you get is a large reduction in *casual* exposure: the token is no longer
sitting in a plaintext file that any tool wanders into while doing something
else. You do not get isolation from code running as you.

## Human consent for writes

Every one of the 16 mutating tools requires a person to approve the exact change
before it is sent to YNAB:

`create_account`, `create_transaction`, `create_transactions`,
`update_transaction`, `update_transactions`, `delete_transaction`,
`import_transactions`, `create_category`, `update_category`,
`create_category_group`, `update_category_group`, `update_category_for_month`,
`update_payee`, `create_scheduled_transaction`, `update_scheduled_transaction`,
`delete_scheduled_transaction`.

The security property is:

> the "before" shown to the human comes from the YNAB API, not from anything the
> model said, and the payload applied afterwards is the one that was shown.

Two mechanisms hold that up.

**The model cannot forge or suppress consent.** A tool parameter annotated
`Context` is injected by the MCP SDK and does not appear in the tool's input
schema. The model cannot supply it, cannot fake it, and cannot leave it out.
Consent therefore cannot be satisfied by anything the model emits.

**The "before" is read live.** Pre-images come from `_shared.client`, which
bypasses the cache entirely. A stale cached row would show you a false "before",
which would make the whole prompt worse than useless. Each call site then
fingerprints the resolved payload before eliciting and asserts the fingerprint
afterwards, so nothing can be re-resolved between the prompt and the write.

Bulk operations itemise **every** row with its own diff. They are never
summarised as "12 transactions" — that is exactly the prompt a person waves
through without having read it. A long prompt is the correct outcome there.

`import_transactions` has no meaningful diff, because YNAB decides what gets
imported. It is gated anyway: the prompt names the linked accounts that may be
affected and states plainly that the result is not knowable in advance.

### If your client cannot elicit

**Writes are refused outright.** There is no silent fallback that applies the
change unconfirmed. If the client did not advertise MCP elicitation support, or
the elicitation request fails, the tool returns an error explaining that the
write was blocked and how to fix it.

This is intended behaviour, but it is worth knowing before you hit it mid-task:
confirm which of your MCP clients actually implement `elicitation/create`. On any
that do not, this server becomes read-only in practice.

## Cache encryption

The local SQLite cache holds payees, memos, amounts and category names — a fairly
complete picture of your finances — in a file under your user profile.

The payload columns are encrypted with **AES-256-GCM**. The key is 256 bits from
`os.urandom`, generated on first use and stored base64 in the OS credential store
under the entry `cache_key`. The envelope is `nonce(12) || ciphertext || tag`,
with a storage-layer framing byte in front so the format can be identified.

SQLCipher would encrypt the whole file, but it needs a native build that is
painful to install on Windows. This is a column-level scheme instead, and that
choice has consequences, listed below.

### What stays in plaintext

These columns are needed for lookups and delta sync and are **not** encrypted:

`plan_id`, `entity_type`, `entity_id`, `cache_key`, `is_deleted`, `cached_at`,
`ttl_seconds`, `knowledge`, `last_synced_at`.

This leaks **metadata**: how many entities of each type you have, which plans
exist, and when the server last synced. It does not leak amounts, payees, memos
or category names.

### The AAD row-swap limitation

The additional authenticated data is a fixed `mcp-ynab:<table>.<column>`. That
binds a ciphertext to its table and column, but **not to its row**. Someone with
write access to the database file could swap ciphertexts between rows of the same
table, and decryption would succeed.

This is acceptable because it requires write access to the DB in the first place,
at which point they can simply corrupt the cache — and the cache is disposable
data that rebuilds itself from YNAB. It is documented rather than hidden.

### File permissions

On POSIX the DB file and its WAL sidecars are set to `0600`. On Windows there is
no portable equivalent; the file inherits the user-profile ACL, which excludes
other non-administrator users but not you or anything running as you.

### Turning it off

`YNAB_CACHE_ENCRYPTION=0` stores the cache in plaintext. This exists for
debugging. If no credential store is available at all, the server **fails closed**
with a message naming this flag, rather than quietly writing plaintext while you
believe the cache is encrypted.

## Read-only mode

`YNAB_READ_ONLY=1` stops the 16 mutating tools being registered at all. They
never appear in the model's tool list, so there is nothing to call and nothing to
be talked out of — a stronger position than offering a tool that then refuses.

It is **off by default**: writes stay enabled unless you opt in.

## Operations

### Store or rotate your token

```bash
mcp-ynab auth login
```

Reads the token with `getpass` (hidden, never in `argv` or shell history),
validates it against `GET /user`, and only then stores it. An invalid token is
refused rather than saved.

Input is invisible as you type or paste — that is `getpass` working, not a hang.
On the Windows console, Ctrl+V at a hidden prompt is delivered as a literal
control character rather than pasting; right-click usually pastes instead. If
your terminal will not cooperate, pipe the token from a file:

```bash
mcp-ynab auth login --stdin < token.txt && rm token.txt
```

In PowerShell, the clipboard works directly and leaves nothing on disk:

```powershell
Get-Clipboard | mcp-ynab auth login --stdin
```

`--stdin` is also the headless/CI path. It keeps the token out of `argv` and out
of shell history, which is the property that matters; `echo <token> | ...` does
not, because the token lands in history. Running it again replaces the stored token, which is
how you rotate: revoke the old one at
<https://app.ynab.com/settings/developer>, create a new one, run `auth login`.

```bash
mcp-ynab auth status   # which source is in use, and a fingerprint — never the token
mcp-ynab auth logout   # delete the stored token
```

After migrating, **remove `YNAB_API_KEY` from your MCP client config and from
`.env.local`**. The credential store takes precedence over the environment, so
leaving a stale key there is not a functional problem — it is exactly the
plaintext exposure this was meant to remove. `auth status` warns when it sees
one.

### Purge cached budget data

```bash
mcp-ynab cache purge
```

Deletes the cache database, its WAL sidecars, and the cache key. The cache
rebuilds itself from YNAB on the next request.

Do this if you suspect the cache file has been exposed, or after revoking a
token.

### Strict setup

```
YNAB_ALLOW_ENV_KEY=0
```

Refuses the `YNAB_API_KEY` environment variable outright, so the credential store
is the only accepted source. Without this, an environment variable is still
honoured — with a deprecation warning on stderr — so existing installs keep
working.

## Credential resolution order

1. OS credential store (`mcp-ynab` / `api_key`)
2. `YNAB_API_KEY` environment variable or `.env.local` — permitted, with a
   deprecation warning on stderr, unless `YNAB_ALLOW_ENV_KEY=0`
3. Otherwise the server refuses to start and tells you to run `mcp-ynab auth login`

The credential store wins over the environment deliberately, so a fresh
`auth login` takes effect even when a stale key is still in an MCP client config.

## Reporting a vulnerability

Open an issue at
<https://github.com/pragprogrammer/mcp-ynab/issues>. Do not include your YNAB
token, an account ID, or a cache file in the report.
