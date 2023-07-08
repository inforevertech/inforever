/*
  Warnings:

  - You are about to drop the column `from` on the `Post` table. All the data in the column will be lost.
  - You are about to drop the column `to` on the `Post` table. All the data in the column will be lost.
  - Added the required column `address_from` to the `Post` table without a default value. This is not possible if the table is not empty.
  - Added the required column `address_to` to the `Post` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE `Post` DROP COLUMN `from`,
    DROP COLUMN `to`,
    ADD COLUMN `address_from` VARCHAR(191) NOT NULL,
    ADD COLUMN `address_to` VARCHAR(191) NOT NULL;
