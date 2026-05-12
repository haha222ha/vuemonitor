(async()=>{
  try{
    const a=document.querySelector("[id=app]").__vue_app__;
    const p=a.config.globalProperties.$pinia;
    const s=p._s.get("auth");
    if(!s) return "no store";
    await s.login("testuser2026@xhs365.cn","Test2026Abc");
    return "login ok:"+s.isAuthenticated;
  }catch(e){
    return "ERR:"+e.message;
  }
})()
