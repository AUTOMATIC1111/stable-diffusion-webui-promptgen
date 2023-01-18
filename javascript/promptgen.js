
function promptgen_send_to(where, text){
    textarea = gradioApp().querySelector('#promptgen_selected_text textarea')
    textarea.value = text
    updateInput(textarea)

    gradioApp().querySelector('#promptgen_send_to_'+where).click()

    where == 'txt2img' ? switch_to_txt2img() : switch_to_img2img()
}

function promptgen_send_to_txt2img(text){ promptgen_send_to('txt2img', text) }
function promptgen_send_to_img2img(text){ promptgen_send_to('img2img', text) }

function submit_promptgen(){
    var id = randomId()
    requestProgress(id, gradioApp().getElementById('promptgen_results_column'), null, function(){})

    var res = create_submit_args(arguments)
    res[0] = id
    return res
}
