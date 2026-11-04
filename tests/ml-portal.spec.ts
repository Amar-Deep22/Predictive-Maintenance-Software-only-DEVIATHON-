import {test,expect} from "@playwright/test";
test("user buttons compute successive FD001 predictions",async({page})=>{
 await page.goto("/");
 await page.getByRole("spinbutton",{name:"Replay engine (1–100)"}).fill("34");
 await page.getByRole("button",{name:"Start engine and run model",exact:true}).click();
 const result=page.getByLabel("Latest inference result");
 await expect(result).toContainText("1–30");
 await page.getByRole("combobox",{name:"Cycles per click",exact:true}).selectOption("10");
 await page.getByRole("button",{name:"Feed next readings and predict",exact:true}).click();
 await expect(result).toContainText("31–40");
 await expect(result).toContainText("11–40");
 await page.getByRole("button",{name:"View result in 3D",exact:true}).click();
 await expect(page.locator(".scene-container")).toHaveAttribute("data-model-priority",/Low|Medium|High|Critical/);
 await expect(page.getByRole("heading",{name:"3D Digital Twin",exact:true})).toBeVisible();
});
