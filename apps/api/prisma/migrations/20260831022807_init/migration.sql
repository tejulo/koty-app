-- CreateTable
CREATE TABLE "SchemaMigrationMarker" (
    "id" SERIAL NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "SchemaMigrationMarker_pkey" PRIMARY KEY ("id")
);
