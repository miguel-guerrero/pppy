% name=f"adder_{param.WIDTH}"

module ${name} (
    input [9:0] a, [9:0] b, cin
);

assign sum = a + b ${"+ cin" if param.HAS_CIN else ""};

endmodule

% ppio['area'] = param.WIDTH+1
// userResult = ${ppio["area"]}
