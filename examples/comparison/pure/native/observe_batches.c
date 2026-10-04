#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <inttypes.h>
extern void bagaev_probe_entry(const int64_t arguments[8], void *output);
static int read_exact(const char *name,void *buf,size_t n){
 FILE *f=fopen(name,"rb");if(!f)return 0;
 int ok=fread(buf,1,n,f)==n && fgetc(f)==EOF && !ferror(f);
 return fclose(f)==0 && ok;
}
static int same(const unsigned char *out,const unsigned char *expected,const int64_t *args,const int64_t *saved){
 return memcmp(out,expected,32)==0 && memcmp(args,saved,64)==0;
}
static uint64_t ns(const struct timespec *t){return (uint64_t)t->tv_sec*UINT64_C(1000000000)+(uint64_t)t->tv_nsec;}
int main(int argc,char **argv){
 if(argc!=5)return 2;
 errno=0;char *end=NULL;unsigned long calls=strtoul(argv[3],&end,10);
 if(errno || !*argv[3] || *end || calls>1000000)return 2;
 errno=0;unsigned long batches=strtoul(argv[4],&end,10);
 if(errno || !*argv[4] || *end || batches>21 || (calls==0 ? batches!=0 : batches==0))return 2;
 _Alignas(8) int64_t args[8],saved[8];_Alignas(8) unsigned char out[32],expected[32];
 if(!read_exact(argv[1],args,64)||!read_exact(argv[2],expected,32))return 3;
 memcpy(saved,args,64);memset(out,0xa5,32);bagaev_probe_entry(args,out);
 if(!same(out,expected,args,saved))return 4;
 if(calls==0){puts("{\"schema\":\"probe-batch-check/1\",\"matches\":true}");return 0;}
 uint64_t times[21];
 for(unsigned batch=0;batch<batches;batch++){
  struct timespec before,after;
  if(clock_gettime(CLOCK_MONOTONIC,&before))return 5;
  for(unsigned long i=0;i<calls;i++)bagaev_probe_entry(args,out);
  if(clock_gettime(CLOCK_MONOTONIC,&after))return 5;
  if(!same(out,expected,args,saved)||ns(&after)<ns(&before))return 4;
  times[batch]=ns(&after)-ns(&before);
 }
 printf("{\"schema\":\"probe-warm-batches/1\",\"calls_per_batch\":%lu,\"matches\":true,\"elapsed_ns\":[",calls);
 for(unsigned i=0;i<batches;i++)printf("%s%" PRIu64,i?",":"",times[i]);
 puts("]}");return ferror(stdout)?6:0;
}
