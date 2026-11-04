import {test,expect} from "@playwright/test";
test("alerts explain urgency without asserting replacement",async({page})=>{
 await page.goto("/");
 await page.getByRole("button",{name:"Fault Alerts",exact:true}).click();
 const alert=page.locator(".fd-order").filter({hasText:"#1 · Engine 034"});
 await expect(alert).toContainText("6.9");
 await expect(alert).toContainText("Does it need replacement?");
 await expect(alert).toContainText("Not established.");
 await alert.getByRole("button",{name:"Review evidence for Engine 034",exact:true}).click();
 await expect(page.getByRole("combobox",{name:"Selected engine",exact:true})).toHaveValue("FD001:test:034");
});
