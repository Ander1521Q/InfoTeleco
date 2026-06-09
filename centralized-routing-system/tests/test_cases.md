# Centralized Routing System - Test Cases

## Test Suite 1: FR-01 Router Registration

### TC-01-01: Single Router Registration
**Steps:**
1. Start controller
2. Start router R1
3. Check controller logs

**Expected:** Router registered successfully

### TC-01-02: Multiple Router Registration
**Steps:**
1. Start R1, R2, R3, R4
2. Execute 'routers' command

**Expected:** All 4 routers appear

## Test Suite 2: FR-02 Neighbor Exchange

### TC-02-01: Send Neighbor Info
**Steps:**
1. On R1: add neighbor R2 cost 2
2. Send topology update

**Expected:** Controller shows link R1-R2

## Test Suite 3: FR-03 Topology Storage

### TC-03-01: Complete Topology
**Build topology:**
- R1: R2(2), R3(5), R4(4)
- R2: R1(2), R3(1)
- R3: R1(5), R2(1), R4(3)
- R4: R1(4), R3(3)

**Expected:** Complete graph with 5 links

## Test Suite 4: FR-04 Dijkstra

### TC-04-01: Shortest Path R1 to R3
**Expected:** Cost 3, path R1->R2->R3

## Test Suite 5: FR-05 Routing Tables

### TC-05-01: R1 Routing Table
| Destination | Next Hop | Cost |
|-------------|----------|------|
| R2 | R2 | 2 |
| R3 | R2 | 3 |
| R4 | R4 | 4 |

## Test Suite 6: FR-06 Table Delivery

### TC-06-01: Broadcast Tables
**Steps:**
1. Complete topology
2. Refresh tables

**Expected:** All routers receive tables

## Test Suite 7: FR-07 Visualization

### TC-07-01: Display Table
**Steps:**
1. Type 'table' in router CLI

**Expected:** Formatted table displayed

## Test Suite 8: FR-08 Link Update

### TC-08-01: Update Cost
**Steps:**
1. Update R1-R2 from 2 to 10
2. Check R1 to R3 path

**Expected:** Path changes to direct R1-R3 (cost 5)

## Test Suite 9: FR-09 Logging

### TC-09-01: Verify Logs
**Check for:**
- Registration events
- Topology updates
- Dijkstra execution
- Table delivery