import frappe
from erpnext.foms.doctype.foms_integration_settings.foms_integration_settings import FomsAPI,is_enable_integration, get_farm_id

@frappe.whitelist()
def get_data():
    api = FomsAPI()

    foms_batch = api.get_all_batch()
    foms_batch2 = [
      {
        "rawMaterialId": 1,
        "batchRefNo": "RM-SS-NBS-BN00001",
        "dateOfCreation": "2021-10-12T00:00:00",
        "qtyAdd": 500000,
        "qtyUsed": 0,
        "qtyReconcilled": 0,
        "qtyLeft": 500000,
        "unitCost": 1,
        "quantityUOM": "g",
        "totalCost": 500000,
        "expiryDate": "2022-06-01T00:00:00",
        "lossRatePercent": 2,
        "rackNumbers": None,
        "warehouseName": None,
        "warehouseId": 0,
        "warehouseRefId": None,
        "supplierId": 0,
        "supplierName": None,
        "supplierRefId": None,
        "status": "Expired",
        "isSeed": False,
        "id": 1
      },
      {
        "rawMaterialId": 2,
        "batchRefNo": "RM-NN-AA-BN00001",
        "dateOfCreation": "2021-10-12T00:00:00",
        "qtyAdd": 100000,
        "qtyUsed": 0,
        "qtyReconcilled": 0,
        "qtyLeft": 100000,
        "unitCost": 1,
        "quantityUOM": "ml",
        "totalCost": 100000,
        "expiryDate": "2022-06-01T00:00:00",
        "lossRatePercent": 1,
        "rackNumbers": None,
        "warehouseName": None,
        "warehouseId": 0,
        "warehouseRefId": None,
        "supplierId": 0,
        "supplierName": None,
        "supplierRefId": None,
        "status": "Expired",
        "isSeed": True,
        "id": 2
      },
      {
        "rawMaterialId": 3,
        "batchRefNo": "RM-NN-BB-BN00001",
        "dateOfCreation": "2021-10-12T00:00:00",
        "qtyAdd": 100000,
        "qtyUsed": 0,
        "qtyReconcilled": 0,
        "qtyLeft": 100000,
        "unitCost": 1,
        "quantityUOM": "L",
        "totalCost": 100000,
        "expiryDate": "2022-06-01T00:00:00",
        "lossRatePercent": 0,
        "rackNumbers": None,
        "warehouseName": None,
        "warehouseId": 0,
        "warehouseRefId": None,
        "supplierId": 0,
        "supplierName": None,
        "supplierRefId": None,
        "status": "Expired",
        "isSeed": False,
        "id": 3
      },
      {
        "rawMaterialId": 4,
        "batchRefNo": "RM-NN-CC-BN00001",
        "dateOfCreation": "2021-10-12T00:00:00",
        "qtyAdd": 100000,
        "qtyUsed": 0,
        "qtyReconcilled": 0,
        "qtyLeft": 100000,
        "unitCost": 1,
        "quantityUOM": "kg",
        "totalCost": 100000,
        "expiryDate": "2022-06-01T00:00:00",
        "lossRatePercent": 1,
        "rackNumbers": [
          "R07-07-06"
        ],
        "warehouseName": "Test warehouse",
        "warehouseId": 1,
        "warehouseRefId": "WH-SG-00001",
        "supplierId": 0,
        "supplierName": None,
        "supplierRefId": None,
        "status": "Expired",
        "isSeed": False,
        "id": 4
    }]

    data = []
    for d in foms_batch.get("items") or []:
        d = frappe._dict(d)
        d.foms_qty = d.qtyLeft
        d.batch_no = d.batchRefNo
        d.erp_qty = frappe.get_value("Batch", d.batch_no, "batch_qty" )
        data.append(d)

    return data