# Case 006: Recipe Management

## Frontmatter
- **Tags**: recipe, udt, array, load, save, data-block, intermediate
- **CPU**: Both
- **Complexity**: Intermediate

## Requirements
Store up to 10 recipes in a global DB. Each recipe contains process parameters
(Name, Speed, Temperature, Pressure, CycleTime, BatchSize). Provide FC_LoadRecipe
to copy a recipe slot into an active working DB, and FC_SaveRecipe to save current
working parameters back to a recipe slot. Three recipes are pre-filled at startup.

## Block Structure
| Block | Type | Purpose |
|-------|------|---------|
| UDT_Recipe | UDT | Recipe parameter structure |
| FC_LoadRecipe | FC | Copy recipe from storage to active working DB |
| FC_SaveRecipe | FC | Copy active working params back to recipe slot |
| DB_Recipes | DB | Storage for 10 recipes |
| DB_ActiveRecipe | DB | Currently active working parameters |
| Main (OB1) | OB | Demonstrates load/save via input triggers |

## SCL Code
```scl
TYPE "UDT_Recipe"
VERSION : 0.1
  STRUCT
    Name        : STRING[32];
    Speed       : REAL;
    Temperature : REAL;
    Pressure    : REAL;
    CycleTime   : TIME;
    BatchSize   : INT;
  END_STRUCT;
END_TYPE

FUNCTION "FC_LoadRecipe" : BOOL
TITLE = 'Load recipe from storage into active working DB'
VERSION : 0.1
VAR_INPUT
  RecipeIndex : INT;
END_VAR
BEGIN
  IF #RecipeIndex < 0 OR #RecipeIndex > 9 THEN
    #FC_LoadRecipe := FALSE;
    RETURN;
  END_IF;

  "DB_ActiveRecipe".Name        := "DB_Recipes".Recipes[#RecipeIndex].Name;
  "DB_ActiveRecipe".Speed       := "DB_Recipes".Recipes[#RecipeIndex].Speed;
  "DB_ActiveRecipe".Temperature := "DB_Recipes".Recipes[#RecipeIndex].Temperature;
  "DB_ActiveRecipe".Pressure    := "DB_Recipes".Recipes[#RecipeIndex].Pressure;
  "DB_ActiveRecipe".CycleTime   := "DB_Recipes".Recipes[#RecipeIndex].CycleTime;
  "DB_ActiveRecipe".BatchSize   := "DB_Recipes".Recipes[#RecipeIndex].BatchSize;
  "DB_ActiveRecipe".ActiveIndex := #RecipeIndex;
  "DB_ActiveRecipe".Loaded      := TRUE;
  #FC_LoadRecipe := TRUE;
END_FUNCTION

FUNCTION "FC_SaveRecipe" : BOOL
TITLE = 'Save active working params back to a recipe slot'
VERSION : 0.1
VAR_INPUT
  RecipeIndex : INT;
END_VAR
BEGIN
  IF #RecipeIndex < 0 OR #RecipeIndex > 9 THEN
    #FC_SaveRecipe := FALSE;
    RETURN;
  END_IF;

  "DB_Recipes".Recipes[#RecipeIndex].Name        := "DB_ActiveRecipe".Name;
  "DB_Recipes".Recipes[#RecipeIndex].Speed       := "DB_ActiveRecipe".Speed;
  "DB_Recipes".Recipes[#RecipeIndex].Temperature := "DB_ActiveRecipe".Temperature;
  "DB_Recipes".Recipes[#RecipeIndex].Pressure    := "DB_ActiveRecipe".Pressure;
  "DB_Recipes".Recipes[#RecipeIndex].CycleTime   := "DB_ActiveRecipe".CycleTime;
  "DB_Recipes".Recipes[#RecipeIndex].BatchSize   := "DB_ActiveRecipe".BatchSize;
  #FC_SaveRecipe := TRUE;
END_FUNCTION

DATA_BLOCK "DB_Recipes"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
  STRUCT
    Recipes : ARRAY[0..9] OF "UDT_Recipe";
  END_STRUCT;
BEGIN
  Recipes[0].Name := 'Standard';
  Recipes[0].Speed := 100.0;
  Recipes[0].Temperature := 180.0;
  Recipes[0].Pressure := 2.5;
  Recipes[0].CycleTime := T#10s;
  Recipes[0].BatchSize := 100;

  Recipes[1].Name := 'HighSpeed';
  Recipes[1].Speed := 250.0;
  Recipes[1].Temperature := 200.0;
  Recipes[1].Pressure := 3.0;
  Recipes[1].CycleTime := T#5s;
  Recipes[1].BatchSize := 200;

  Recipes[2].Name := 'LowTemp';
  Recipes[2].Speed := 80.0;
  Recipes[2].Temperature := 120.0;
  Recipes[2].Pressure := 1.5;
  Recipes[2].CycleTime := T#15s;
  Recipes[2].BatchSize := 50;
END_DATA_BLOCK

DATA_BLOCK "DB_ActiveRecipe"
{ S7_Optimized_Access := 'FALSE' }
VERSION : 0.1
NON_RETAIN
VAR
  ActiveIndex : INT := -1;
  Loaded      : BOOL := FALSE;
  Name        : STRING[32] := '';
  Speed       : REAL := 0.0;
  Temperature : REAL := 0.0;
  Pressure    : REAL := 0.0;
  CycleTime   : TIME := T#0ms;
  BatchSize   : INT := 0;
END_VAR
BEGIN
END_DATA_BLOCK

ORGANIZATION_BLOCK "Main"
VERSION : 0.1
VAR_TEMP
  temp       : INT;
  loadOK     : BOOL;
  saveOK     : BOOL;
  recipeIdx  : INT;
END_VAR
BEGIN
  // Recipe index from HMI or input word (0-9)
  #recipeIdx := BYTE_TO_INT(%IB0);
  IF #recipeIdx > 9 THEN
    #recipeIdx := 0;
  END_IF;

  // Load recipe on rising edge of I1.0
  IF %I1.0 THEN
    #loadOK := "FC_LoadRecipe"(RecipeIndex := #recipeIdx);
  END_IF;

  // Save recipe on rising edge of I1.1
  IF %I1.1 THEN
    #saveOK := "FC_SaveRecipe"(RecipeIndex := #recipeIdx);
  END_IF;
END_ORGANIZATION_BLOCK
```

## MCP Commands Used
```
SetExternalSourceContent(softwarePath="PLC_1/PLC_1", sourceName="main", content=<above SCL>)
GenerateBlocksFromSource(softwarePath="PLC_1/PLC_1", sourceName="main")
CompileSoftware(softwarePath="PLC_1/PLC_1")
DownloadSoftware(softwarePath="PLC_1/PLC_1", downloadOptions="Software")
```

## Key Decisions
- UDT_Recipe as shared type -- used by both DB_Recipes (storage array) and referenced
  field-by-field in DB_ActiveRecipe for runtime flexibility
- Separate DB_ActiveRecipe (working copy) from DB_Recipes (storage) -- prevents
  accidental modification of stored recipes during operation
- FC (not FB) for Load/Save -- stateless operations, no instance DB needed
- Array bounds check (0-9) in both FCs -- prevents out-of-range access
- Return value BOOL indicates success/failure -- caller can react to invalid index
- 3 pre-filled recipes in DB_Recipes BEGIN section -- ready to use after download
- S7_Optimized_Access=FALSE on all DBs for S7.Net runtime monitoring
- Block order: UDT first (dependency), then FCs, then DBs, then OB

## Test Procedure
```
S7Connect(ipAddress="192.168.0.1", cpuType="S71500")

// Verify pre-filled recipes in storage DB
S7ReadDBStruct(dbNumber=1, startByte=0, count=50)   -> Recipe[0] (Standard)
S7ReadVariable(address="DB1.DBD34")                  -> Recipes[0].Speed (REAL, expect 100.0)
S7ReadVariable(address="DB1.DBD38")                  -> Recipes[0].Temperature (REAL, expect 180.0)
S7ReadVariable(address="DB1.DBD42")                  -> Recipes[0].Pressure (REAL, expect 2.5)

// Load recipe 0 into active working DB
S7WriteVariable(address="%IB0", value="0", type="Byte")
S7WriteVariable(address="%I1.0", value="true", type="Bit")
// Read active recipe
S7ReadVariable(address="DB2.DBW0")                   -> ActiveIndex (INT, expect 0)
S7ReadVariable(address="DB2.DBX2.0")                 -> Loaded (BOOL, expect TRUE)
S7ReadVariable(address="DB2.DBD38")                  -> Speed (REAL, expect 100.0)
S7ReadVariable(address="DB2.DBD42")                  -> Temperature (REAL, expect 180.0)

// Modify active recipe speed and save back to slot 3
S7WriteVariable(address="DB2.DBD38", value="150.0", type="Real")
S7WriteVariable(address="%IB0", value="3", type="Byte")
S7WriteVariable(address="%I1.1", value="true", type="Bit")
// Verify saved to slot 3
S7ReadVariable(address="DB1.DBD184")                 -> Recipes[3].Speed (REAL, expect 150.0)

// Load recipe 1 (HighSpeed) and verify
S7WriteVariable(address="%IB0", value="1", type="Byte")
S7WriteVariable(address="%I1.0", value="true", type="Bit")
S7ReadVariable(address="DB2.DBD38")                  -> Speed (REAL, expect 250.0)
S7ReadVariable(address="DB2.DBD42")                  -> Temperature (REAL, expect 200.0)

S7Disconnect()
```
