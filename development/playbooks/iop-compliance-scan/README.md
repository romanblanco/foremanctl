# iop-compliance-scan (DEBUG / lab)

Automates the iop-debug manual flow: provision a genuine RHEL9 client, register
it, create + assign a compliance policy via the compliance-backend **v2 API**,
run an OpenSCAP scan, and fetch the report.

**DEBUG/testing only — not an installer.** Lives on the `add-iop-compliance-debug`
branch. Several inputs are VPN-gated Red Hat mirror artifacts that are not
committed (see `vars/example.yaml`).

## Prerequisites

1. A deployed env: `./forge vms start` + `./foremanctl deploy --add-feature iop ...`
   (see repo `README.md`). SSG must be imported (the `import-ssg` timer; guides
   RHEL-8/9/10 at 0.1.81 verified).
2. A genuine **RHEL9 QCOW2** vagrant box + cloud-init **seed ISO** + keypair, and
   signed **openscap-scanner / scap-security-guide-0.1.81 / insights-client** RPMs
   from `download.devel.redhat.com` (VPN). SSG version must match the server's
   imported content.
3. An inventory containing both the server host `quadlet` (from
   `inventories/local_vagrant`) and the RHEL9 client host.

## Run

```bash
ANSIBLE_COLLECTIONS_PATH="$PWD/build/collections/forge:$PWD/build/collections/foremanctl" \
ansible-playbook -i inventories/local_vagrant -i <rhel9-client inventory> \
  development/playbooks/iop-compliance-scan/iop-compliance-scan.yaml \
  -e @development/playbooks/iop-compliance-scan/vars/example.yaml
```

## Flow

| Play | Host | Does |
|------|------|------|
| 1 | localhost | Provision RHEL9 client (asserts artifacts; `vagrant up` — TODO) |
| 2 | rhel9-client | `/etc/hosts` → server, install scanner/SSG/insights (signed), register |
| 3 | quadlet | Resolve org_id + uuid from `hbi.hosts`, create policy, assign host |
| 4 | rhel9-client | `insights-client --compliance` |
| 5 | quadlet | Poll the policy for the reported system / score |

## API notes (verified live)

- Compliance API is reached by `podman exec`-ing curl inside the
  `iop-service-compliance-backend-api` container (`http://localhost:8000/api/compliance/v2`).
  The host netns can't reach `foreman-core-network`, and the gateway needs a
  client cert / `X-Org-Id`.
- Auth: base64 **User** `X-RH-IDENTITY` with `identity.org_id` +
  `entitlements.insights.is_entitled=true`. `DISABLE_RBAC=true` → permission
  checks pass; no RBAC/UI/CSRF. Do **not** use `auth_type: cert-auth` for create.
- Create: `POST /policies` (`application/vnd.api+json`) body
  `{title, profile_id, compliance_threshold}` → 201. `os_major_version`/`ref_id`
  derive from the profile. Verified: ANSSI enhanced RHEL-9
  `profile_id=e4ed65c6-42c8-49ae-893a-c0ff5fdf1a39` → `os_major=9`.
- Assign: `PATCH /policies/{id}/systems/{uuid}` (no body) → 202. Host `os_major`
  must equal the policy's; one policy per profile type; same org.

## Status

- **Verified live**: API reachability, identity auth, SSG present, profile lookup,
  `POST` create (201), `DELETE` (202).
- **TODO (external)**: play 1 `vagrant up` of the genuine RHEL9 box; the mirror
  RPM URLs/box artifacts in `vars/example.yaml`; the exact Foreman global-
  registration command in play 2.
