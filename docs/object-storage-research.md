
Supabase Storage:
- Limited free tier 
- Can work with s3 but requires a translation layer
- Probably easiest to set up since its aready in the stack

Cloudfare R2:
- 10 GB free
- Can use boto3 -> comptable with s3
- better for lots of downloads + if you want predictable costs if we were to pay for it

Blackblaze B2:
- 10 GB free
- Can use boto3 -> comptable with s3
- Better for cheap large storage with infrequent downloads

MiniIo:
- Can store as much data as hardware lets
- Can use boto3 -> comptable with s3
- Probably the most difficult to set up

Supabase Storage is the best choice for simplest setup but has limited storage in the free tier. Cloudflare R2 is the better option for more free storage and easier S3 compatibility. 
