(async()=>{
  await window.electronAPI.invoke("storage:run","DELETE FROM product_features WHERE product_id=?",["a69edb6b-5e4c-4914-8c7b-31767b571d30"]);
  await window.electronAPI.invoke("storage:run","DELETE FROM products WHERE id=?",["a69edb6b-5e4c-4914-8c7b-31767b571d30"]);
  return "deleted";
})()
