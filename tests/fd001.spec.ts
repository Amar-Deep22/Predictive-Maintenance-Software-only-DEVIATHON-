import { test, expect } from "@playwright/test";

test("FD001 fleet, life cycle, model metrics and saved work orders", async ({page}) => {
  await page.goto("/");
  await page.getByRole("button", {name:"FD001 Maintenance", exact:true}).click();
  const fleet = page.locator(".fd-table tbody tr");
  await expect(fleet).toHaveCount(5);
  await page.getByLabel("Machines displayed").selectOption("4");
  await expect(fleet).toHaveCount(4);
  await page.getByLabel("Machines displayed").selectOption("5");
  await expect(fleet).toHaveCount(5);
  await expect(page.getByText("Estimated end-of-life cycle", {exact:true})).toBeVisible();
  await expect(page.locator(".fd-stats").getByText("14.36", {exact:true})).toBeVisible();
  await expect(page.getByText("19.52", {exact:true})).toBeVisible();
  await page.getByRole("button", {name:"Draft maintenance work order",exact:true}).click();
  await expect(page.getByRole("status")).toContainText("saved on disk");
  const order=page.locator(".fd-order").first();
  await order.getByLabel("Assignee").fill("Browser QA — no equipment action");
  await order.getByLabel("Notes").fill("Persistence check only");
  await order.getByRole("button",{name:"Save work order",exact:true}).click();
  await expect(page.getByRole("status")).toContainText("updated and saved");
  await page.reload();
  await page.getByRole("button",{name:"FD001 Maintenance",exact:true}).click();
  await expect(page.locator(".fd-order").first().getByLabel("Assignee")).toHaveValue("Browser QA — no equipment action");
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
});

 test("animated summary settles on real values and respects reduced motion", async ({page}) => {
  for (const reducedMotion of ["no-preference", "reduce"] as const) {
    await page.emulateMedia({reducedMotion});
    await page.goto("/");
    await page.getByRole("button",{name:"FD001 Maintenance",exact:true}).click();
    const counters=page.locator(".fleet-kpi strong > span[aria-label]");
    await expect(counters).toHaveCount(3);
    for(const counter of await counters.all()) {
      await expect(counter).toHaveText((await counter.getAttribute("aria-label"))!);
    }
    if(reducedMotion==="reduce") {
      await expect(page.locator(".fleet-overview article").first()).toHaveCSS("animation-name","none");
    }
  }
});
