# Dummy Data untuk Unit Testing GP-Modified DocTypes

## Tujuan
Menyimpan sample data (frappe doc format JSON) dari doctype-doctype yang sudah dimodifikasi oleh rizkyGP.
Data ini akan digunakan sebagai fixture/seed untuk unit test yang menguji customisasi kita.

## Sumber Data
- Site: `test4`
- Daftar doctype yang dimodifikasi: `/home/frappe/RIZKY_DOCTYPE_JSON.csv`

## Strategi Pemilihan DocType
Dipilih 3 doctype transaksional dengan record terbanyak (exclude auto-generated ledger entries):

| No | DocType | Record Count | Alasan |
|----|---------|-------------|--------|
| 1 | Sales Invoice | 5099 | Transaksi penjualan utama, banyak custom field |
| 2 | Sales Order | 4368 | Source document penjualan, linked ke SI & DN |
| 3 | Stock Entry | 8904 | Transaksi inventory utama, linked ke manufacturing |

## Isi File

### `savehere.json`
```json
{
  "Sales Invoice": [ ...3 docs... ],
  "Sales Order": [ ...3 docs... ],
  "Stock Entry": [ ...3 docs... ]
}
```

Setiap doc disimpan dalam format `frappe.get_doc().as_dict()` lengkap dengan child table rows.

## Rules Pengambilan Data
- Ambil 3 record **terbaru** (by `modified` desc) per doctype
- Child table (items, taxes, dll) di-include sebagai nested list
- Data mapping fields: maksimal 5 rows per child table
- Sensitive data (jika ada) tetap di-keep karena ini site test

## Penggunaan Selanjutnya
Data ini akan dipakai untuk:
1. Validasi bahwa custom fields terisi dengan benar
2. Regression test setelah patch/migration
3. Fixture untuk pytest unit tests
