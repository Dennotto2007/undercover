import { expect, test } from "@playwright/test";

test("a handler can read the queue, a claim and the instructions", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Claims queue" }),
  ).toBeVisible();
  await expect(page.getByRole("row")).toHaveCount(26);

  await page.getByRole("link", { name: "CLM-1003" }).click();
  await expect(page).toHaveURL(/#\/claims\/CLM-1003$/);
  await expect(page.getByRole("heading", { name: "CLM-1003" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Items claimed" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Policy" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Claim history" }),
  ).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "CLM-1003" })).toBeVisible();

  await page.getByRole("link", { name: "Instructions" }).click();
  await expect(page.getByText("You are the UnderCover Agent.")).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveCount(0);

  await page.getByRole("link", { name: "Queue" }).click();
  await expect(page.getByRole("row")).toHaveCount(26);
});

test("the agent works a claim while the handler watches", async ({ page }) => {
  await page.goto("/#/claims/CLM-1001");
  const status = page.locator(".page-title .chip");
  await expect(status).toHaveText("Waiting");

  await page.getByRole("button", { name: "Run agent" }).click();
  await expect(status).toHaveText("In progress");
  await expect(page.getByText("Reading the claim")).toBeVisible();
  await expect(page.getByText("Approved and paid.")).toBeHidden();

  await expect(
    page.getByText("Recording the decision: approve, $420.00"),
  ).toBeVisible();
  await expect(page.getByText("Approved and paid.")).toBeVisible();
  await expect(status).toHaveText("Decided");
  await expect(page.getByText("Paid", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Queue" }).click();
  const row = page.getByRole("row", { name: /CLM-1001/ });
  await expect(row.getByText("Decided")).toBeVisible();
  await expect(row.getByText("Approved")).toBeVisible();
});

test("a payout over the limit waits for a handler to sign off", async ({
  page,
}) => {
  await page.goto("/#/claims/CLM-1002");
  await page.getByRole("button", { name: "Run agent" }).click();

  const status = page.locator(".page-title .chip");
  await expect(status).toHaveText("Waiting for sign-off");
  await expect(page.getByText(/Payment blocked/)).toBeVisible();
  await expect(page.getByText("Paid", { exact: true })).toBeHidden();

  await page.getByLabel("Handler").selectOption({ label: "Dana Whitfield" });
  await page.getByRole("button", { name: "Sign off and pay" }).click();

  await expect(status).toHaveText("Decided");
  await expect(page.getByText("Signed off by")).toBeVisible();
  await expect(page.getByText("Dana Whitfield")).toBeVisible();
  await expect(page.getByText("Paid", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Sign off and pay" }),
  ).toBeHidden();
});
