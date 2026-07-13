# Design: Repeat Harvest Product Linking

## Overview

Fitur untuk menangani tanaman yang bisa dipanen berkali-kali (multi-harvest crops) — di mana satu kali tanam menghasilkan beberapa cycle panen dengan periode waktu tertentu.

**Referensi PRD:** `docs/superpowers/files/Product Requirement Document_ Repeat Harvest Product Linking.md`

---

## Business Context

### Current State
- Setiap harvest cycle dikelola sebagai produk independent (`PR-HV-BSA`, `PR-HV-BSB`, `PR-HV-BSC`)
- User harus manual create request untuk setiap harvest
- Manual hitung kapan harvest berikutnya
- Tidak ada visibility bahwa produk-produk ini satu cycle
- FOMS langsung trigger Work Order di ERPNext

### Target State
- Admin setup Repeat Harvest Group (parent + child products + gap)
- Request untuk parent otomatis generate Repeat Harvest Items
- Setiap Repeat Harvest Item → Work Order sendiri
- Dashboard/calendar menampilkan parent-child relationship
- Stock Entry pakai child item, tapi inventory map ke parent

---

## ERPNext Architecture Mapping

### New DocTypes Required

#### 1. `Repeat Harvest Group` (DocType - Config/Setup)

> **Fungsi:** Konfigurasi hubungan parent-child harvest. Ini DocType setup, bukan transaksional.

```python
fields = [
    "group_name",              # Data (unique) — contoh: "Basil Harvest Cycle"
    "parent_item",             # Link → Item (produk induk)
    "is_active",               # Check
    "different_harvest_dates", # Check
    "harvest_gap_in_days",     # Int — jeda antar harvest dalam hari
    "naming_series",           # Select: RHG-.YYYY.-.#####
]
```

#### 2. `Repeat Harvest Item` (DocType - Transaksional, Standalone)

> **Fungsi:** Setiap harvest instance dalam satu group. Punya lifecycle sendiri, bukan child table.

```python
fields = [
    "naming_series",           # Select: RHI-.YYYY.-.#####
    "repeat_harvest_group",    # Link → Repeat Harvest Group
    "item",                    # Link → Item (child harvest product)
    "sequence",                # Int urutan harvest
    "harvest_date_offset",     # Int (hari dari parent start date)
    "planned_harvest_date",    # Date — dihitung saat WO di-generate
    "actual_harvest_date",     # Date — diisi saat harvest selesai
    "status",                  # Select: Draft/Planned/In Progress/Completed/Cancelled
    "work_order",              # Link → Work Order (WO yang di-generate)
    "qty",                     # Float — quantity yang di-harvest
    "uom",                     # Link → UOM
    "lot_id",                  # Data — Lot ID dari Work Order
    "remarks",                 # Small Text
]
```

### Modifications to Existing DocTypes

#### Work Order (field additions)

```python
# Tambahan field di Work Order:
repeat_harvest_group = Link("Repeat Harvest Group")
repeat_harvest_item = Link("Repeat Harvest Item")
harvest_sequence = Int()
parent_harvest_product = Link("Item")
```

#### Item (field additions)

```python
# Tidak perlu tambah field ke Item
# Grouping dipegang oleh Repeat Harvest Group DocType
# Setiap harvest instance dipegang oleh Repeat Harvest Item DocType
# Item tetap bersih, tidak terpengaruh
```

---

## Flow Implementation

### 1. Admin Setup Flow

```
Admin Portal > Product Module > Repeat Harvest Setup
    ↓
Step 1: Create Repeat Harvest Group (CONFIG DocType)
    - Group Name: "Basil Harvest Cycle"
    - Select Parent Product: PR-HV-BSA
    - Enable "Different Harvesting Dates"
    - Set Harvest Gap: 14 days
    - Save & Activate
    ↓
Step 2: Create Repeat Harvest Items (TRANSACTION DocType, linked to Group)
    - Item: PR-HV-BSB, Sequence: 1, Harvest Date Offset: 14
    - Item: PR-HV-BSC, Sequence: 2, Harvest Date Offset: 28
    - Status: Draft
    - (Bisa juga auto-generated saat parent WO dibuat)
```

### 2. Request Generation Flow (FOMS → ERPNext)

> **UPDATE: Trigger flow ada di FOMS**

```
FOMS create Work Order untuk PR-HV-BSA
    ↓
ERPNext terima Work Order dari FOMS
    ↓
ERPNext controller (on_submit atau on_insert):
    1. Cek apakah production_item punya active Repeat Harvest Group
    2. Kalau iya:
       a. Query Repeat Harvest Group
       b. Query/Create Repeat Harvest Items untuk tiap child product
       c. Calculate harvest dates berdasarkan gap
       d. Generate Work Orders untuk tiap Repeat Harvest Item
       e. Link semua WO ke Repeat Harvest Items
       f. Update Repeat Harvest Item status → "Planned"
    3. Kalau tidak: treat sebagai normal Work Order
    ↓
Semua Repeat Harvest Items di-link ke same Repeat Harvest Group
    ↓
FOMS manage execution (Seeding → Transplanting → Harvesting)
```

### 3. Work Order Generation Logic

```python
def generate_repeat_harvest_work_orders(parent_wo):
    """Generate child Work Orders based on Repeat Harvest Group"""

    # 1. Get active Repeat Harvest Group for the parent item
    rhg = frappe.db.get_value(
        "Repeat Harvest Group",
        {"parent_item": parent_wo.production_item, "is_active": 1},
        ["name", "harvest_gap_in_days"],
        as_dict=True
    )

    if not rhg:
        return  # No repeat harvest setup, process as normal

    # 2. Get Repeat Harvest Items for this group
    rhi_items = frappe.get_all(
        "Repeat Harvest Item",
        filters={"repeat_harvest_group": rhg.name},
        fields=["name", "item", "sequence", "harvest_date_offset", "status"],
        order_by="sequence asc"
    )

    if not rhi_items:
        return  # No harvest items configured

    # 3. Calculate harvest dates and create Work Orders
    base_date = parent_wo.planned_start_date

    for rhi in rhi_items:
        # Skip if already planned or completed
        if rhi.status in ("Planned", "In Progress", "Completed"):
            continue

        # Calculate planned start date
        if rhi.harvest_date_offset:
            planned_date = base_date + timedelta(days=rhi.harvest_date_offset)
        else:
            planned_date = base_date + timedelta(
                days=rhg.harvest_gap_in_days * rhi.sequence
            )

        # Get BOM for child item
        bom = frappe.db.get_value(
            "BOM",
            {"item": rhi.item, "is_active": 1, "is_default": 1},
            "name"
        )

        if not bom:
            continue

        # Create Work Order
        child_wo = frappe.new_doc("Work Order")
        child_wo.update({
            "production_item": rhi.item,
            "bom_no": bom,
            "qty": parent_wo.qty,  # Same qty as parent
            "company": parent_wo.company,
            "fg_warehouse": parent_wo.fg_warehouse,
            "planned_start_date": planned_date,
            "repeat_harvest_group": rhg.name,
            "repeat_harvest_item": rhi.name,  # Link ke standalone DocType
            "harvest_sequence": rhi.sequence,
            "parent_harvest_product": parent_wo.production_item,
        })

        # Copy required items from BOM
        child_wo.set_required_items()
        child_wo.insert(ignore_permissions=True)

        # Update Repeat Harvest Item dengan WO link dan status
        frappe.db.set_value("Repeat Harvest Item", rhi.name, {
            "work_order": child_wo.name,
            "planned_harvest_date": planned_date,
            "status": "Planned"
        })
```

---

## Display Requirements

### Operations Task List

Format: `Child Product ID (Parent Product ID)`

```
PR-HV-BSC (PR-HV-BSA)
```

### Calendar View

```
14 Jul 2026  |  PR-HV-BSB (PR-HV-BSA)  |  Planned
28 Jul 2026  |  PR-HV-BSC (PR-HV-BSA)  |  Planned
```

### Dashboard Filters

- Parent product
- Child product
- Repeat harvest group
- Harvest date
- Lot ID
- Status

---

## ERP Sync Logic

> **UPDATE (2026-07-10): Tidak ada perubahan akunting. Accounting tetap lengkap Seeding → Transplanting → Harvesting untuk SETIAP harvest cycle.**

### Current Understanding (Dari PRD + Update)

1. Stock Entry tetap pakai `item_code` child product
2. Quantity di-parent product di ERP inventory (virtual mapping)
3. **Tidak ada proses merge/repack** — setiap product punya stock sendiri
4. **Accounting tetap lengkap** — setiap cycle punya cost yang sama

### Implementation Approach

**Phase 1: Basic Linking**
- Stock Entry pakai child item_code
- Custom field di Stock Entry untuk reference parent
- Report/dashboard filter by parent

**Phase 2: Enhanced Reporting**
- Custom reports untuk parent-child relationship
- Dashboard filters
- Calendar view

```python
# Di Stock Entry atau custom DocType:
# Tambah field untuk tracking:
repeat_harvest_group = Link("Repeat Harvest Group")
repeat_harvest_item = Link("Repeat Harvest Item")
parent_product = Link("Item")
harvest_sequence = Int()
```

### Future Enhancement (Phase 2)

- Proses merge/repack: child stock → parent stock
- UOM conversion jika diperlukan
- Journal entry untuk cost allocation

---

## Validation Rules

### Repeat Harvest Group (Config)
1. `parent_item` harus exist di Item Master
2. `harvest_gap_in_days` >= 0
3. Inactive group tidak trigger auto-generation
4. `group_name` harus unique

### Repeat Harvest Item (Transactional)
1. `item` harus exist di Item Master
2. `repeat_harvest_group` harus exist dan active
3. `item` tidak boleh duplikat dalam satu group
4. `sequence` tidak boleh duplikat dalam satu group
5. Status transition: Draft → Planned → In Progress → Completed
6. Status transition: Draft/Planned → Cancelled (kapan saja)
7. Tidak bisa cancel jika status = In Progress (harus complete atau fail dulu)

---

## Edge Cases

| Case | Behavior |
|------|----------|
| Parent tanpa active setup | Treat sebagai normal WO |
| Repeat Harvest Item dibatalkan | Hanya RHI itu yang batal, lainnya tetap. WO juga dibatalkan |
| Parent dibatalkan (belum ada child mulai) | Cancel semua RHI dan WO terkait |
| Parent dibatalkan (sudah ada child mulai) | Perlu konfirmasi user. RHI yang sudah complete tetap, sisanya cancel |
| Harvest gap diubah setelah request | Tidak auto-update existing RHI. Admin harus manual update atau re-plan |
| ERP sync gagal | RHI status = "Failed Sync", WO tetap completed |
| Duplicate parent request | Generate RHI terpisah dengan Lot ID berbeda |
| RHI tanpa Work Order | Status tetap "Draft", bisa di-generate ulang |
| Work Order dibatalkan | Update RHI status = "Cancelled" |

---

## Scope

> **⚠️ UNKNOWN: Phase priority belum ditentukan - perlu keputusan bisnis**

### Phase 1 (Core) - Minimal Viable Feature
- [ ] Repeat Harvest Group DocType (config/setup)
- [ ] Repeat Harvest Item DocType (standalone, transaksional)
- [ ] Work Order field additions (repeat_harvest_group, repeat_harvest_item, harvest_sequence, parent_harvest_product)
- [ ] Auto-generation logic di Work Order controller
- [ ] Basic display format (child + parent reference)
- [ ] Repeat Harvest Item status management

### Phase 2 (Dashboard & Reporting) - Visibility
- [ ] Calendar view custom
- [ ] Dashboard filters
- [ ] Custom reports

### Phase 3 (ERP Sync & Integration) - Accounting
- [ ] Stock Entry mapping
- [ ] Inventory parent-child mapping
- [ ] Merge/repack process (future)

---

## Accounting & Manufacturing Analysis

> **UPDATE (2026-07-10): Accounting tetap lengkap Seeding → Transplanting → Harvesting untuk SETIAP harvest cycle. Tidak ada perubahan akunting.**

### Manufacturing Flow (Updated)

```
Cycle 1: Seeding → Transplanting → Harvesting (1 Juli)
Cycle 2: Seeding → Transplanting → Harvesting (14 Juli)  
Cycle 3: Seeding → Transplanting → Harvesting (28 Juli)
```

**Key Insight:** Setiap harvest cycle — termasuk cycle ke-2, ke-3, dst — tetap melalui **full manufacturing process** (Seeding → Transplanting → Harvesting). Tidak ada shortcut atau skip operasi.

### BOM Strategy

**Satu BOM untuk semua harvest cycles** — BOM yang sama dipakai berulang kali:

| Harvest | BOM yang Dipakai | Operations |
|---------|------------------|------------|
| Pertama | BOM Default | Seeding + Transplanting + Harvesting |
| Kedua | BOM Default (sama) | Seeding + Transplanting + Harvesting |
| Ketiga | BOM Default (sama) | Seeding + Transplanting + Harvesting |

**Implikasi:** Tidak perlu multiple BOM. Tiap child product menggunakan BOM yang sama dengan parent.

### Cost Accumulation

```
Cycle 1: Full cost (Seeding + Transplanting + Harvesting)
Cycle 2: Full cost (sama dengan Cycle 1)
Cycle 3: Full cost (sama dengan Cycle 1)
```

**Setiap cycle punya cost yang SAMA** — tidak ada perbedaan cost antar cycles.

### Work Order Structure

```python
# Cycle 1: Full Work Order
WO-BSA:
  operations: [Seeding, Transplanting, Harvesting]
  required_items: [seeds, seedlings, packaging]
  cost: Full

# Cycle 2: Full Work Order (sama)
WO-BSB:
  operations: [Seeding, Transplanting, Harvesting]
  required_items: [seeds, seedlings, packaging]
  cost: Full (sama dengan WO-BSA)

# Cycle 3: Full Work Order (sama)
WO-BSC:
  operations: [Seeding, Transplanting, Harvesting]
  required_items: [seeds, seedlings, packaging]
  cost: Full (sama dengan WO-BSA)
```

### Inventory Impact

```
Cycle 1:
  - Input: Seeds, Seedlings → WIP → Output: PR-HV-BSA
  - Stock: PR-HV-BSA masuk inventory

Cycle 2:
  - Input: Seeds, Seedlings → WIP → Output: PR-HV-BSB
  - Stock: PR-HV-BSB masuk inventory
  - Note: Full process, bukan harvest-only

Cycle 3:
  - Input: Seeds, Seedlings → WIP → Output: PR-HV-BSC
  - Stock: PR-HV-BSC masuk inventory
  - Note: Full process, bukan harvest-only
```

### Accounting Implications

| Aspek | Status | Detail |
|-------|--------|--------|
| **BOM** | Tidak berubah | Satu BOM untuk semua cycles |
| **Cost** | Tidak berubah | Setiap cycle punya cost yang sama |
| **Operations** | Tidak berubah | Semua cycles melalui Seeding → Transplanting → Harvesting |
| **Inventory** | Tidak berubah | Tiap product punya stock sendiri |

**Kesimpulan:** Tidak ada perubahan akunting. Fitur ini hanya menambah **linking dan scheduling** antar harvest cycles, bukan mengubah manufacturing process.

---

## Trigger Flow

> **UPDATE (2026-07-10): Trigger flow ada di FOMS, bukan di ERPNext.**

### Current Flow (FOMS → ERPNext)

```
FOMS create Work Order → ERPNext terima → Create WO
```

### Updated Flow with Repeat Harvest

```
FOMS create Work Order untuk parent (PR-HV-BSA)
    ↓
ERPNext cek: apakah parent punya active Repeat Harvest Group?
    ↓ (ya)
ERPNext query/create Repeat Harvest Items untuk tiap child product
    ↓
ERPNext auto-generate child Work Orders:
    - WO untuk PR-HV-BSB (dengan BOM yang sama) → link ke RHI
    - WO untuk PR-HV-BSC (dengan BOM yang sama) → link ke RHI
    ↓
Update Repeat Harvest Items status → "Planned"
    ↓
FOMS manage execution (Seeding → Transplanting → Harvesting)
```

### Implementation Notes

1. **FOMS remains the trigger** — ERPNext tidak create WO langsung
2. **ERPNext adds linking logic** — Saat terima WO dari FOMS, cek apakah ada Repeat Harvest Group
3. **Repeat Harvest Items** — Setiap child product punya Repeat Harvest Item (standalone DocType)
4. **Auto-generate child WOs** — Jika ada, generate WO lainnya dengan scheduling yang benar, link ke Repeat Harvest Items
5. **BOM unchanged** — Semua WO pakai BOM yang sama
6. **Cost unchanged** — Tidak ada perbedaan cost antar cycles

---

## Open Questions (Untuk Dibahas Direksi)

> **Status: UNKNOWN - Perlu keputusan bisnis sebelum implementasi**

### 1. ~~Trigger Mechanism~~ ✅ RESOLVED
- Trigger flow ada di FOMS
- ERPNext hanya menerima dan menambah linking logic

### 2. ~~BOM Strategy~~ ✅ RESOLVED
- Satu BOM untuk semua harvest cycles
- Tidak perlu multiple BOM

### 3. ~~Quantity Handling~~ ✅ RESOLVED
- Quantity child = quantity parent (atau configurable)
- Tidak ada yield/regrowth difference

### 4. Naming Convention
- Bagaimana naming untuk generated Work Orders?
- **Option A:** Ikut parent WO naming + sequence (MFG-WO-2026-0001-1)
- **Option B:** Independent naming series
- **Status:** Belum ditentukan

### 5. ~~Approval Flow~~ ✅ RESOLVED
- FOMS sudah handle approval flow
- ERPNext hanya menerima dan link

### 6. ERP Sync Mapping
- Bagaimana cara map quantity child ke parent product di inventory?
- Apakah perlu custom DocType atau Stock Entry field?
- Atau ada proses merge/repack yang sudah ada?
- **Status:** Belum ditentukan

### 7. Calendar/Dashboard Location
- Apakah calendar view di ERPNext Workspace atau custom page?
- Apakah ada existing calendar yang bisa di-extend?
- **Status:** Belum ditentukan

### 8. Cancellation Rules
- Jika parent dibatalkan, apakah semua child harus dibatalkan?
- Atau ada threshold (misal: jika >50% child sudah complete, tidak bisa cancel)?
- **Status:** Belum ditentukan

### 9. Reporting Requirements
- Report mana saja yang perlu di-modify untuk support repeat harvest?
- Apakah ada existing report yang bisa di-extend?
- **Status:** Belum ditentukan

### 10. Phase Priority
- Apakah ada prioritas phase tertentu yang harus duluan?
- Atau semua phase bisa dikerjakan sequential?
- **Status:** Belum ditentukan

---

## Success Metrics

1. Manual creation berkurang (target: 100% otomatis)
2. Production bisa identify linked products via Repeat Harvest Item
3. Missed harvest planning berkurang
4. ERP inventory visibility di parent level lebih baik
5. Cancel child (RHI) tanpa affect parent/child lain
6. Repeat Harvest Item status tracking memberikan visibility lebih baik
7. Work Order ↔ Repeat Harvest Item link memberikan traceability

---

*Last updated: 2026-07-13*
*Status: Draft - Analisis & Diskusi*
