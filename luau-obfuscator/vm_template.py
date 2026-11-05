"""Luau VM interpreter as a Python string, with {SEED} placeholder."""

VM_TEMPLATE = r'''local sD={SEED}
local kK=(sD*31+7)%251+1
local function xR(a,b)
local r,p=0,1
while a>0 or b>0 do
if a%2~=b%2 then r=r+p end
a,b,p=a//2,b//2,p*2
end
return r
end
local function gG(t,k)
local v=t[k]
if v==nil and getgenv then v=getgenv()[k] end
if v==nil and shared then v=shared[k] end
return v
end
local function runX(data)
local U=unpack or table.unpack
local B={}
for i=1,#data do B[i]=xR(data:byte(i),(kK+i)%256) end
local P=1
local function r1() local v=B[P] P=P+1 return v end
local function r2() local v=B[P]+B[P+1]*256 P=P+2 return v end
local nP=r2() local nS=r2() local om=r1()
local rp={}
for i=1,om do rp[r1()]=i end
local SS={}
for i=1,nS do
local k=r1() local l=r2() local s={}
for j=1,l do s[j]=string.char(xR(B[P],k)) P=P+1 end
SS[i]=table.concat(s)
end
local PP={}
for i=1,nP do
local p={}
p.np=r1() p.va=r1()==1 p.nl=r2()
local nI=r2() local nC=r2() local nU=r1()
p.ii={}
for j=1,nI do p.ii[j]={r1(),r2(),r2()} end
p.cc={}
for j=1,nC do
local tp=r1()
if tp==0 then p.cc[j]=nil
elseif tp==1 then p.cc[j]=r1()==1
elseif tp==2 then
local l=r2() local s={}
for k=1,l do s[k]=string.char(B[P]) P=P+1 end
p.cc[j]=tonumber(table.concat(s))
elseif tp==3 then p.cc[j]=SS[r2()] end
end
p.uu={}
for j=1,nU do p.uu[j]={inStack=r1()==1,idx=r1()} end
PP[i]=p
end
local function EX(cl,ar)
local pr=cl.proto
local LL={}
local UV=cl.upvals
local ST={}
local sp=0
local VA={}
for i=0,pr.np-1 do LL[i]={v=ar[i+1]} end
if pr.va then
for i=pr.np+1,#ar do VA[#VA+1]=ar[i] end
end
local pc=1
local ii=pr.ii
local cc=pr.cc
while true do
local inst=ii[pc]
local op=rp[inst[1]]
local A=inst[2]
pc=pc+1
if op==nil then
elseif op==1 then sp=sp+1 ST[sp]=cc[A+1]
elseif op==2 then sp=sp+1 ST[sp]=nil
elseif op==3 then sp=sp+1 ST[sp]=true
elseif op==4 then sp=sp+1 ST[sp]=false
elseif op==5 then ST[sp]=nil sp=sp-1
elseif op==6 then ST[sp+1]=ST[sp] sp=sp+1
elseif op==7 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a+b
elseif op==8 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a-b
elseif op==9 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a*b
elseif op==10 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a/b
elseif op==11 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a%b
elseif op==12 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a^b
elseif op==13 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a//b
elseif op==14 then ST[sp]=-ST[sp]
elseif op==15 then ST[sp]=not ST[sp]
elseif op==16 then ST[sp]=#ST[sp]
elseif op==17 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a..b
elseif op==18 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a==b
elseif op==19 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a~=b
elseif op==20 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a<b
elseif op==21 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a<=b
elseif op==22 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a>b
elseif op==23 then local b=ST[sp] local a=ST[sp-1] sp=sp-1 ST[sp]=a>=b
elseif op==24 then sp=sp+1 ST[sp]=LL[A].v
elseif op==25 then LL[A].v=ST[sp] ST[sp]=nil sp=sp-1
elseif op==26 then sp=sp+1 ST[sp]=gG(_G,cc[A+1])
elseif op==27 then _G[cc[A+1]]=ST[sp] ST[sp]=nil sp=sp-1
elseif op==28 then sp=sp+1 ST[sp]=UV[A].v
elseif op==29 then UV[A].v=ST[sp] ST[sp]=nil sp=sp-1
elseif op==30 then sp=sp+1 ST[sp]={}
elseif op==31 then local o=ST[sp] ST[sp]=o[cc[A+1]]
elseif op==32 then local v=ST[sp] local o=ST[sp-1] sp=sp-1 o[cc[A+1]]=v ST[sp]=nil sp=sp-1
elseif op==33 then local k=ST[sp] local o=ST[sp-1] sp=sp-1 ST[sp]=o[k]
elseif op==34 then local v=ST[sp] local k=ST[sp-1] local o=ST[sp-2] sp=sp-2 o[k]=v ST[sp]=nil sp=sp-1
elseif op==35 then
local na=A
local ca={}
for i=na,1,-1 do ca[i]=ST[sp] ST[sp]=nil sp=sp-1 end
local fn=ST[sp] ST[sp]=nil sp=sp-1
local result
if fn==nil then
error("[VM] attempt to call nil (opcode 35)")
elseif type(fn)=="table" and fn.__c then
result=EX(fn,ca)
elseif type(fn)=="function" then
result=fn(U(ca))
else
error("[VM] attempt to call "..type(fn).." (opcode 35)")
end
sp=sp+1 ST[sp]=result
elseif op==36 then
local o=ST[sp]
ST[sp]=o[cc[A+1]]
sp=sp+1 ST[sp]=o
elseif op==37 then
local n=A
local vals={}
for i=n,1,-1 do vals[i]=ST[sp] ST[sp]=nil sp=sp-1 end
return vals[1]
elseif op==38 then return nil
elseif op==39 then pc=pc+A-1
elseif op==40 then local v=ST[sp] ST[sp]=nil sp=sp-1 if v then pc=pc+A-1 end
elseif op==41 then local v=ST[sp] ST[sp]=nil sp=sp-1 if not v then pc=pc+A-1 end
elseif op==42 then
local cp=PP[A+1]
local nU={}
for i,uv in ipairs(cp.uu) do
if uv.inStack then nU[i]=LL[uv.idx]
else nU[i]=UV[uv.idx] end
end
sp=sp+1 ST[sp]={__c=true,proto=cp,upvals=nU}
elseif op==43 then
for i=1,#VA do sp=sp+1 ST[sp]=VA[i] end
end
end
end
return EX({proto=PP[1],upvals={}},{})
end
'''
