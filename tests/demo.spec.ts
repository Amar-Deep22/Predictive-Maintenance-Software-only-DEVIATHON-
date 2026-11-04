import {test,expect} from "@playwright/test";
test("current ML demo navigation and real 3D canvas",async({page})=>{
 await page.goto("/");
 await page.getByRole("button",{name:"Machines",exact:true}).click();
 await page.getByRole("combobox",{name:"Machines displayed",exact:true}).selectOption("4");
 await expect(page.locator(".fd-table tbody tr")).toHaveCount(4);
 await page.getByRole("combobox",{name:"Machines displayed",exact:true}).selectOption("5");
 await expect(page.locator(".fd-table tbody tr")).toHaveCount(5);
 await page.getByRole("button",{name:"Inspect Engine 034",exact:true}).click();
 await expect(page.locator("canvas")).toBeVisible();
 await expect(page.getByText("3D rendering unavailable",{exact:true})).toHaveCount(0);
 for(const name of ["Front","Side","Top","Isometric","Cutaway","Pause visual motion"]){
  await page.getByRole("button",{name,exact:true}).click();
 }
 await page.getByRole("button",{name:"Model Evaluation",exact:true}).click();
 await expect(page.getByRole("link",{name:"Download evaluation CSV"})).toBeVisible();
});
