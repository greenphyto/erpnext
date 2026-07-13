# Product Requirement Document: Repeat Harvest Product Linking

## Feature Name

**Repeat Harvest Product Linking**

## Background

Some crops, such as basil, can be harvested multiple times through a regrowth cycle\. Today, each harvest cycle is managed using separate product codes\.

Example:

Currently, users need to manually create and plan each harvest product separately\. For example, if the first basil harvest starts on **1 July**, the user must manually remember to trigger the second basil harvest around **14 July**, after the first harvest cycle is completed\.

This approach gives flexibility and clean accounting, but creates manual planning effort and weak visibility between related harvests\.

## Current Workflow

Today, repeat harvest products are handled as independent products\.

Example:

1. User creates or triggers request for `PR-HV-BSB`\.

2. The first harvest is planned and executed\.

3. User manually calculates the next harvest date\.

4. User creates or triggers request for `PR-HV-BSC`\.

5. Production team treats `PR-HV-BSB` and `PR-HV-BSC` as separate products\.

6. ERP inventory stores them as separate items\.

## Current Benefits

The existing approach has several benefits:

1. **Each harvest has its own Lot ID**
Each product produced can be tracked independently\.

2. **Each harvest can be closed individually**
The first harvest and second harvest can be completed, cancelled, or adjusted separately\.

3. **Products can be used independently**
Each harvest product can be sold individually or used as part of a mixed product\.

4. **Accounting is clean**
Cost accumulation and product closing are handled clearly per product and per lot\.

## Current Pain Points

The existing process also creates several issues:

1. **Inventory is split across separate products**
Production and inventory teams may not clearly see that these products belong to the same parent crop\.

2. **No linkage between related harvests**
Production does not know that `PR-HV-BSB` and `PR-HV-BSC` are part of the same basil repeat harvest cycle\.

3. **Manual date calculation is required**
Users must manually calculate the time gap between harvest requests\.

4. **Higher risk of missed planning**
If the user forgets to create the second harvest request, the subsequent regrowth harvest may not be planned\.

5. **Limited dashboard visibility**
Dashboards show each product separately without clearly identifying the parent repeat\-harvest relationship\.

## Objective

The objective of this feature is to keep the benefits of separate product handling while removing the manual effort and visibility issues\.

The system should allow users to define a parent repeat\-harvest product and link it to multiple child harvest products\. When a request is created for the parent product, the system should automatically generate the relevant Repeat Harvest Items with the correct harvest dates\.

## Goals

The feature should:

1. Allow admin users to link repeat\-harvest products together\.

2. Support a parent\-child product structure\.

3. Allow child products to be arranged in harvest order\.

4. Automatically generate Repeat Harvest Items when the parent product is requested\.

5. Automatically calculate the harvest date gap between child products\.

6. Preserve separate Lot IDs for each child product\.

7. Allow each Repeat Harvest Item to be cancelled or closed individually\.

8. Show parent product reference in operations tasks and dashboards\.

9. Support ERP sync using the parent product inventory mapping\.

10. Improve visibility in the calendar view for upcoming repeat harvest orders\.

## Proposed Solution

A new sub\-module will be created under the **Product Module** in the Admin Portal\.

This sub\-module will allow users to configure repeat\-harvest product relationships\.

The user can:

1. Select a **Parent Product**\.

2. Add one or more **Child Products**\.

3. Define the harvest sequence\.

4. Define the harvest date gap between each child product\.

5. Choose whether the child products have different harvesting dates\.

6. Activate or deactivate the repeat harvest setup\.

Example setup:

When a request is created for `PR-HV-BSA`, the system will automatically generate Repeat Harvest Items for:

1. `PR-HV-BSB`

2. `PR-HV-BSC`

Each Repeat Harvest Item will have its own planned harvest date, Lot ID, task flow, and closure status\.

## User Flow

### 9\.1 Admin Configuration Flow

1. User goes to **Admin Portal \> Product Module \> Repeat Harvest Setup**\.

2. User clicks **Create Repeat Harvest Group**\.

3. User selects parent product, for example `PR-HV-BSA`\.

4. User selects the option **Different Harvesting Dates**\.

5. User adds child product `PR-HV-BSB`\.

6. User sets sequence as `1`\.

7. User adds child product `PR-HV-BSC`\.

8. User sets sequence as `2`\.

9. User sets harvest gap between child products, for example `14 days`\.

10. User saves and activates the repeat harvest group\.

### 9\.2 Planning Flow

1. Marketing or production creates a request for parent product `PR-HV-BSA`\.

2. System checks whether `PR-HV-BSA` has an active repeat harvest setup\.

3. System automatically generates Repeat Harvest Items based on the configured sequence\.

4. System assigns different planned harvest dates based on the configured gap\.

5. Each Repeat Harvest Item is planned separately\.

6. Each child product gets its own Lot ID\.

7. The generated requests are shown in the planning calendar\.

Example:

### 9\.3 Operations Flow

In operations tasks, child products will be shown with the parent product reference in brackets\.

Example:

This allows production users to clearly understand that the task belongs to a repeat harvest cycle under the parent basil product\.

### 9\.4 Dashboard Flow

The production dashboard should also display the parent product reference\.

Example:

The dashboard should allow users to filter by:

1. Parent product

2. Child product

3. Repeat harvest group

4. Harvest date

5. Lot ID

6. Status

## ERP Sync Logic

For linked repeat\-harvest products, ERP sync should map the harvested quantity back to the parent product inventory\.

Example:

This means that although FOMS manages the Repeat Harvest Items separately for planning, production, Lot ID, and closure, the final ERP inventory quantity can be synced to the parent product\.

The ERP sync should include reference information to trace which Repeat Harvest Item generated the quantity\.

Recommended ERP sync reference fields:

1. Parent Product ID

2. Child Product ID

3. Repeat Harvest Group ID

4. Lot ID

5. Harvest Date

6. Harvest Sequence

7. Harvest Quantity

8. Sync Status

## Quantity Handling

When a parent product request is created, the system should generate Repeat Harvest Items based on the parent requested quantity\.

Example:

Generated child requests:

The first version can use the same requested quantity for each child product unless a future configuration is added for quantity split or expected regrowth yield\.

Future enhancement:

## Calendar View Requirement

The new calendar view should clearly show upcoming Repeat Harvest Items\.

For example, if basil repeat harvest is requested, the calendar should show:

This gives the team better visibility of upcoming basil orders and allows them to adjust ERP requests where required\.

The calendar should visually indicate:

1. Parent product

2. Child product

3. Sequence number

4. Planned harvest date

5. Request status

6. Whether the Repeat Harvest Item is active, cancelled, or completed

## Cancellation Requirement

Users should be able to cancel subsequent Repeat Harvest Items without cancelling the whole repeat harvest group\.

Example:

1. `PR-HV-BSB` is already planned and harvested\.

2. Production or marketing decides that `PR-HV-BSC` is not required\.

3. User cancels only the `PR-HV-BSC` Repeat Harvest Item\.

4. `PR-HV-BSB` remains completed\.

5. Parent repeat harvest group remains traceable\.

This is important because production and demand may change after the first harvest\.

## Functional Requirements

### 14\.1 Repeat Harvest Setup

The system shall allow admin users to create:
1. **Repeat Harvest Group** \- Configuration DocType defining the parent\-child relationship
2. **Repeat Harvest Items** \- Transactional DocType representing each harvest instance

Required fields for Repeat Harvest Group:
\- Group Name (unique)
\- Parent Product (Link → Item)
\- Is Active (Check)
\- Different Harvesting Dates (Check)
\- Harvest Gap in Days (Int)

Required fields for Repeat Harvest Item:
\- Repeat Harvest Group (Link)
\- Item (Link → Item)
\- Sequence (Int)
\- Harvest Date Offset (Int)
\- Status (Select)
\- Planned Harvest Date (Date)
\- Work Order (Link → Work Order)

### 14\.2 Parent Product Validation

The system shall validate that:

1. A parent product exists in the product master\.

2. A child product exists in the product master\.

3. A child product cannot be duplicated within the same repeat harvest group\.

4. Sequence order cannot be duplicated\.

5. Harvest gap must be zero or greater\.

6. An inactive repeat harvest group should not trigger automatic child requests\.

### 14\.3 Request Generation

When a parent product request is created, the system shall:

1\. Check whether the parent product has an active Repeat Harvest Group\.

2\. Create/update Repeat Harvest Items for each child product\.

3\. Assign planned harvest dates based on the configured harvest gap\.

4\. Link all Repeat Harvest Items to the same Repeat Harvest Group\.

5\. Generate Work Orders linked to each Repeat Harvest Item\.

6\. Assign separate Lot IDs to each Repeat Harvest Item\.

7\. Display parent product reference in operations and dashboard views\.

### 14\.4 Operations Display

The system shall display repeat harvest child products in this format:

`Child Product ID (Parent Product ID)`

Example:

`PR-HV-BSC (PR-HV-BSA)`

This display format should apply to:

1. Operations task list

2. Harvesting task view

3. Production dashboard

4. Calendar view

5. Reports

6. Request detail page

### 14\.5 ERP Sync

The system shall sync linked repeat harvest quantities to the parent product inventory item in ERP\.

The sync should retain Repeat Harvest Item references for traceability\.

For example if `PR-HV-BSC`is harvested, it it saved as inventory of `PR-HV-BSA`,which is different from mixed product\. 

### 14\.6 Status Management

Each Repeat Harvest Item shall have its own status\.

Example statuses:

1. Planned

2. In Progress

3. Completed

4. Cancelled

5. Failed Sync

6. Synced to ERP

Parent repeat harvest status should be derived from child statuses\.

Example:

## Edge Cases

### 16\.1 Parent Product Requested Without Active Setup

If the parent product does not have an active repeat harvest setup, the system should treat it as a normal product request\.

### 16\.2 Child Product Cancelled

If a Repeat Harvest Item is cancelled, the system should not cancel the other Repeat Harvest Items automatically\.

### 16\.3 Parent Product Cancelled

If the parent request is cancelled before any child task starts, the system should cancel all generated Repeat Harvest Items\.

If some Repeat Harvest Items have already started or completed, the system should require user confirmation before cancelling the remaining Repeat Harvest Items\.

### 16\.4 Harvest Gap Changed After Request Creation

If the admin changes the harvest gap after Repeat Harvest Items have already been generated, existing Repeat Harvest Items should not be automatically changed unless the user explicitly chooses to re\-plan them\.

### 16\.5 ERP Sync Failure

If ERP sync fails, the Repeat Harvest Item should remain completed in FOMS but show ERP sync status as failed\.

The user should be able to retry ERP sync\.

### 16\.6 Duplicate Parent Request

If a parent product is requested multiple times on the same date, each request should generate its own Repeat Harvest Items and Lot IDs\.

## Reporting Requirements

Reports and dashboards should support:

1. Parent product filter

2. Child product filter

3. Repeat harvest group filter

4. Harvest sequence filter

5. Planned harvest date

6. Actual harvest date

7. Quantity requested

8. Quantity harvested

9. ERP sync status

10. Cancellation status

## Success Metrics

The feature is successful if:

1. Manual creation of Repeat Harvest Items is reduced\.

2. Production can clearly identify linked repeat harvest products\.

3. Missed second\-harvest planning cases are reduced\.

4. ERP inventory visibility is cleaner at parent product level\.

5. Users can cancel future Repeat Harvest Items without affecting completed harvests\.

6. Calendar view provides clear visibility of upcoming repeat harvest demand\.



