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
