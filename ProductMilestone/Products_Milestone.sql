with filtered_atlas_dates as (
  select
    item.EnterpriseItemId as AtlasProjectItemId,
    item.Name as AtlasProjectName,
    item.ItemType as AtlastProjectItemType,
    Milestone__Base as Milestone,
    coalesce(
      milestones.Actual__Finish, milestones.Trend, milestones.POR, milestones.DriveTo
    ) as MilestoneDate,
    milestones.PLC__Order as MilestoneOrder,
    milestones.Stepping__Name as Stepping,
    project.PlanningState as AtlasProjectPlanningState,
    CONCAT('https://atlas.intel.com/ProductDashboard/', item.EnterpriseItemId) AS `Atlas-link`
  from
    z_product_engineering_ibi.atlas.atlas_product_milestones milestones
      inner join z_product_engineering_ibi.traceit.onebom_item_type item
        on (milestones.Speed__ID = item.EnterpriseItemid)
      inner join z_product_engineering_ibi.atlas.atlas_project_list project
        on (project.ProductID = milestones.Speed__ID)
  where
    milestones.Enabled = true
    and milestones.PLC__Order is not null
    and item.Name LIKE ANY ('Nova%Lake%', 'Razor%Lake%', 'Titan%Lake%', 'Hammer%Lake%', 'PIXE3%', '%Dunlow%')
    AND item.Name NOT LIKE '%Base%'
    AND (item.ItemType = 'Die' OR item.ItemType = 'Si Product' OR item.ItemType = 'Finished Good Group')
    AND project.PlanningState IS NOT NULL
    AND UPPER(TRIM(project.PlanningState)) NOT IN ('CANCELLED', 'CANCELED', 'INVALID', 'ABANDONED')
    AND milestones.Stepping__Name != 'null'
)

select distinct
  f.AtlasProjectItemId,
  f.AtlasProjectName,
  f.AtlastProjectItemType,
  f.Milestone,
  f.MilestoneDate,
  f.MilestoneOrder,
  f.Stepping,
  f.AtlasProjectPlanningState,
  int(cal.`Intel Year-Work Week`) as MilestoneDateYYYYWW,
  NULL as Comment,
  f.`Atlas-link`
from
  filtered_atlas_dates f
    inner join z_product_engineering_ibi.ipg.cv_dg_calendar_v3 cal
      on (f.MilestoneDate = cal.`Calendar Date`)

union all

select distinct
  f.AtlasProjectItemId,
  f.AtlasProjectName,
  f.AtlastProjectItemType,
  'Sort PO*' as Milestone,
  date_add(WEEK, 14, f.MilestoneDate) as MilestoneDate,
  f.MilestoneOrder,
  f.Stepping,
  f.AtlasProjectPlanningState,
  int(cal.`Intel Year-Work Week`) as MilestoneDateYYYYWW,
  'Estimate ~TI+14WW' as Comment,
  f.`Atlas-link`
from
  filtered_atlas_dates f
    inner join z_product_engineering_ibi.ipg.cv_dg_calendar_v3 cal
      on (date_add(WEEK, 14, f.MilestoneDate) = cal.`Calendar Date`)
where f.Milestone = 'Tape In'

order by MilestoneDateYYYYWW asc