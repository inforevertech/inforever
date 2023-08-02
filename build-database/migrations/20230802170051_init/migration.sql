-- CreateTable
CREATE TABLE `Post` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `hash` VARCHAR(191) NOT NULL,
    `block` VARCHAR(191) NULL,
    `text` LONGTEXT NOT NULL,
    `formatted_text` LONGTEXT NULL,
    `love_counter` INTEGER NOT NULL DEFAULT 0,
    `applause_counter` INTEGER NOT NULL DEFAULT 0,
    `fire_counter` INTEGER NOT NULL DEFAULT 0,
    `brain_counter` INTEGER NOT NULL DEFAULT 0,
    `laugh_counter` INTEGER NOT NULL DEFAULT 0,
    `alarm_counter` INTEGER NOT NULL DEFAULT 0,
    `money_counter` INTEGER NOT NULL DEFAULT 0,
    `timestamp` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `nonsense` BOOLEAN NOT NULL DEFAULT false,
    `network` VARCHAR(191) NOT NULL DEFAULT 'inforever',
    `postedLocally` BOOLEAN NOT NULL DEFAULT false,
    `author` VARCHAR(191) NULL,
    `donation` DOUBLE NULL,
    `fee` DOUBLE NULL,
    `fullPost` BOOLEAN NOT NULL DEFAULT true,
    `isReply` BOOLEAN NOT NULL DEFAULT false,
    `replyToHash` VARCHAR(191) NULL,

    UNIQUE INDEX `Post_id_key`(`id`),
    UNIQUE INDEX `Post_hash_key`(`hash`),
    FULLTEXT INDEX `Post_text_idx`(`text`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Address` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `address` VARCHAR(191) NOT NULL,
    `direction` BOOLEAN NOT NULL,
    `network` VARCHAR(191) NOT NULL DEFAULT 'btc-test',
    `post_hash` VARCHAR(191) NOT NULL,

    UNIQUE INDEX `Address_id_key`(`id`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- CreateTable
CREATE TABLE `Media` (
    `id` INTEGER NOT NULL AUTO_INCREMENT,
    `filename` VARCHAR(191) NOT NULL,
    `type` VARCHAR(191) NOT NULL,
    `timestamp` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    `post_hash` VARCHAR(191) NULL,

    UNIQUE INDEX `Media_id_key`(`id`),
    PRIMARY KEY (`id`)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- AddForeignKey
ALTER TABLE `Post` ADD CONSTRAINT `Post_replyToHash_fkey` FOREIGN KEY (`replyToHash`) REFERENCES `Post`(`hash`) ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Address` ADD CONSTRAINT `Address_post_hash_fkey` FOREIGN KEY (`post_hash`) REFERENCES `Post`(`hash`) ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE `Media` ADD CONSTRAINT `Media_post_hash_fkey` FOREIGN KEY (`post_hash`) REFERENCES `Post`(`hash`) ON DELETE SET NULL ON UPDATE CASCADE;
