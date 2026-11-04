export const components: Record<string,{name:string;sensors:number[];guidance:string}> = {
 fan:{name:'Fan',sensors:[1,8,13],guidance:'Review fan inlet temperature and fan-speed trends. FD001 does not establish a fan fault.'},
 lpc:{name:'Low-pressure compressor',sensors:[2],guidance:'Review outlet-temperature trends. Inspect only under the applicable procedure; no LPC diagnosis is available.'},
 hpc:{name:'High-pressure compressor',sensors:[3,7,11],guidance:'Review outlet temperature and pressures. HPC degradation is the FD001 scenario; arrange engineering review when engine RUL is low.'},
 combustor:{name:'Combustor',sensors:[12,16],guidance:'Review fuel-flow and fuel-air-ratio readings. These are context signals, not a combustor fault diagnosis.'},
 hpt:{name:'High-pressure turbine',sensors:[20],guidance:'Review HPT coolant-bleed readings. No turbine-specific fault prediction is available.'},
 lpt:{name:'Low-pressure turbine',sensors:[4,21],guidance:'Review outlet temperature and coolant-bleed readings. No turbine-specific fault prediction is available.'},
 exhaust:{name:'Exhaust',sensors:[],guidance:'No dedicated exhaust measurement is provided here. Visual model only; use approved inspection procedures.'},
 lp_shaft:{name:'Low-pressure shaft',sensors:[8,13],guidance:'Fan-speed readings provide spool context, not shaft or bearing condition.'},
 hp_shaft:{name:'High-pressure shaft',sensors:[9,14],guidance:'Core-speed readings provide spool context, not a shaft fault diagnosis.'},
 bearings:{name:'Bearings',sensors:[],guidance:'FD001 supplies no dedicated bearing vibration sensor or bearing-fault labels. Bearing diagnosis is unavailable.'},
 accessory_gearbox:{name:'Accessory gearbox',sensors:[],guidance:'No dedicated gearbox sensors or gearbox-fault labels are available in FD001.'},
 bypass_duct:{name:'Bypass duct',sensors:[6,15],guidance:'Review bypass pressure and bypass-ratio readings for context. No duct-specific diagnosis is available.'},
};
